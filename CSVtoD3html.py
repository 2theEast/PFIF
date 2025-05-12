#!/usr/bin/env python
# coding: utf-8

import os
import json
import pandas as pd
from urllib.parse import urlparse

# --- Config ---
csv_path = "https://github.com/2theEast/PFIF/blob/main/USAF_PFIF_Tree.csv"

# --- Helpers ---

def sanitize_url(url):
    """Extract base domain from URL or mark as 'Unavailable'."""
    if not isinstance(url, str) or url.strip() == "" or url.lower() in {"nan", "none"}:
        return "Unavailable"
    try:
        parsed = urlparse(url)
        return parsed.netloc if parsed.netloc else "Unavailable"
    except Exception:
        return "Unavailable"

def clean_hierarchy_columns(df, columns=["parent", "child", "subchild"]):
    """Normalize hierarchy values and remove junk placeholders."""
    invalid_values = {"", "unknown", "n/a", "null", "none", "unavailable"}

    def normalize(value):
        if not isinstance(value, str):
            return None
        value = value.strip().lower()
        return None if value in invalid_values else value.strip()

    for col in columns:
        if col in df.columns:
            df[col] = df[col].apply(normalize)
    return df

def build_tree_from_clean_df(df):
    """Build nested hierarchy for D3.js based on cleaned data."""
    root = {"name": "Start Here", "children": []}
    parent_dict = {}

    for _, row in df.iterrows():
        p = row["parent"]
        c = row.get("child")
        s = row.get("subchild")
        resource = row["resource_name"]
        tooltip = row.get("tooltip", "")
        url = row.get("clean_url", "Unavailable")

        if p not in parent_dict:
            parent_node = {"name": p, "children": []}
            parent_dict[p] = parent_node
            root["children"].append(parent_node)
        else:
            parent_node = parent_dict[p]

        if not c:
            target_node = parent_node
        else:
            child_node = next((n for n in parent_node["children"] if n["name"] == c), None)
            if not child_node:
                child_node = {"name": c, "children": []}
                parent_node["children"].append(child_node)

            if s:
                sub_node = next((n for n in child_node["children"] if n["name"] == s), None)
                if not sub_node:
                    sub_node = {"name": s, "children": []}
                    child_node["children"].append(sub_node)
                target_node = sub_node
            else:
                target_node = child_node

        resource_node = {
            "name": resource,
            "tooltip": tooltip,
            "url": url
        }
        target_node.setdefault("children", []).append(resource_node)

    def prune_empty(node):
        if "children" in node:
            node["children"] = [prune_empty(child) for child in node["children"]]
            node["children"] = [child for child in node["children"] if child is not None]
            if not node["children"]:
                node.pop("children")
        return node

    return prune_empty(root)

def has_unknowns(node):
    """Recursively check for any node with 'name': 'unknown'."""
    if str(node.get("name", "")).strip().lower() == "unknown":
        return True
    return any(has_unknowns(child) for child in node.get("children", []))


# --- Main Workflow ---

# Step 1: Load and clean the CSV
df = pd.read_csv(csv_path)
df.columns = df.columns.str.strip().str.lower()

# Step 2: Normalize URLs
df["clean_url"] = df["url"].apply(sanitize_url)

# Step 3: Clean hierarchy fields
cleaned_df = clean_hierarchy_columns(df.copy())

# Step 4: Build final hierarchical tree
final_tree = build_tree_from_clean_df(cleaned_df)

# Step 5: Final validation
if has_unknowns(final_tree):
    print("⚠️ Tree still contains 'unknown' nodes.")
else:
    print("✅ Tree cleaned successfully. No 'unknown' entries remain.")

# Optional: Save as JSON
json_output_path = os.path.splitext(csv_path)[0] + "_tree.json"
with open(json_output_path, "w", encoding="utf-8") as f:
    json.dump(final_tree, f, indent=2)

print(f"Tree saved to: {json_output_path}")


# In[3]:


print("Available columns after cleaning:", df.columns.tolist())


# In[4]:


# Build a clean hierarchical tree from DataFrame
def build_tree(df):
    root = {"name": "PFIF", "children": []}
    parent_dict = {}

    for _, row in df.iterrows():
        p = row.get("parent", "").strip()
        c = row.get("child", "").strip()
        s = row.get("subchild", "").strip() if "subchild" in df.columns else ""
        r = row["resource_name"].strip()
        tooltip = row.get("tooltip", "").strip()
        url = row.get("clean_url", "Unavailable").strip()

        # Skip if required fields are missing
        if not p or p.lower() == "unknown":
            continue

        # Add or get parent node
        if p not in parent_dict:
            parent_node = {"name": p, "children": []}
            parent_dict[p] = parent_node
            root["children"].append(parent_node)
        else:
            parent_node = parent_dict[p]

        # Initialize target node as parent
        target_node = parent_node

        # Add or get child node if valid
        if c and c.lower() != "unknown":
            child_node = next((n for n in parent_node["children"] if n["name"] == c), None)
            if not child_node:
                child_node = {"name": c, "children": []}
                parent_node["children"].append(child_node)
            target_node = child_node

            # Add or get subchild node if valid and distinct from resource
            if s and s.lower() != "unknown" and s != r:
                sub_node = next((n for n in child_node["children"] if n["name"] == s), None)
                if not sub_node:
                    sub_node = {"name": s, "children": []}
                    child_node["children"].append(sub_node)
                target_node = sub_node

        # Add the resource node to the final target
        resource_node = {
            "name": r,
            "tooltip": tooltip,
            "url": url
        }
        target_node["children"].append(resource_node)

    return root


# In[5]:


# --- Dangling Category Validation ---

from collections import defaultdict

# Create sets for unique levels
parent_set = set(df['parent'].dropna())
child_set = set(df['child'].dropna())
subchild_set = set(df['subchild'].dropna()) if 'subchild' in df.columns else set()

# Track issues
dangling_children = set()
dangling_subchildren = set()

# Check: Are there any child entries whose parent is missing?
for child in child_set:
    parent_rows = df[df['child'] == child]
    if not parent_rows['parent'].isin(parent_set).any():
        dangling_children.add(child)

# Check: Are there any subchild entries whose child is missing?
if 'subchild' in df.columns:
    for subchild in subchild_set:
        child_rows = df[df['subchild'] == subchild]
        if not child_rows['child'].isin(child_set).any():
            dangling_subchildren.add(subchild)

# Report results
if dangling_children or dangling_subchildren:
    print("⚠️ Potential structure issues detected:\n")
    if dangling_children:
        print("  - Dangling 'child' values without valid parent:")
        for item in dangling_children:
            print(f"    • {item}")
    if dangling_subchildren:
        print("\n  - Dangling 'subchild' values without valid child:")
        for item in dangling_subchildren:
            print(f"    • {item}")
else:
    print("✅ No dangling children or subchildren detected. Hierarchy appears valid.")


# In[6]:


print("Unique parent values:\n", df['parent'].dropna().unique())


# In[7]:


print("Unique Parent Values:")
print(df["parent"].value_counts())


# In[9]:


# Clean your DataFrame first
cleaned_df_full = clean_hierarchy_columns(df.copy(), columns=["parent", "child", "subchild"])

# Then build the tree
final_tree = build_tree_from_clean_df(cleaned_df_full)

# Updated tree builder that handles pre-cleaned DataFrame
def build_tree_from_clean_df(df):
    root = {"name": "Start Here", "children": []}
    parent_dict = {}

    for _, row in df.iterrows():
        p = row["parent"]
        c = row.get("child")
        s = row.get("subchild")
        resource = row["resource_name"]
        tooltip = row.get("tooltip", "")
        url = row.get("url", "Unavailable")

        # Get or create parent node
        if p not in parent_dict:
            parent_node = {"name": p, "children": []}
            parent_dict[p] = parent_node
            root["children"].append(parent_node)
        else:
            parent_node = parent_dict[p]

        # Determine where to attach the resource
        if not c:
            target_node = parent_node
        else:
            # Get/create child node
            child_node = next((n for n in parent_node["children"] if n["name"] == c), None)
            if not child_node:
                child_node = {"name": c, "children": []}
                parent_node["children"].append(child_node)

            if s:
                # Get/create subchild node
                sub_node = next((n for n in child_node["children"] if n["name"] == s), None)
                if not sub_node:
                    sub_node = {"name": s, "children": []}
                    child_node["children"].append(sub_node)
                target_node = sub_node
            else:
                target_node = child_node

        # Add the resource node
        resource_node = {
            "name": resource,
            "tooltip": tooltip,
            "url": url
        }
        target_node.setdefault("children", []).append(resource_node)

    # Prune empty children
    def prune_empty(node):
        if "children" in node:
            node["children"] = [prune_empty(child) for child in node["children"]]
            node["children"] = [child for child in node["children"] if child is not None]
            if not node["children"]:
                node.pop("children")
        return node

    return prune_empty(root)

# Rebuild tree with the updated function
final_tree = build_tree_from_clean_df(cleaned_df_full)

# Confirm final check
has_unknowns(final_tree)


# In[10]:


#| **Section**                    | **Customization**                        |
#| ------------------------------ | ---------------------------------------- |
#| `header`                       | Title, colors, and branding              |
#| `.tooltip` CSS                 | Size, color, font of tooltips            |
#| `circle` node styles           | Colors for expanded/collapsed nodes      |
#| `text` label styles            | Font size, positioning, outline          |
#| `.attr("viewBox", ...)`        | Controls how much of the tree is visible |
#| `tree().nodeSize([...])`       | Spacing between nodes                    |
#| `window.open(d.data.url)`      | Control link behavior                    |
#| `tooltip.html(d.data.tooltip)` | Use richer HTML content or conditionals  |


# In[14]:


# HTML template with instructional comments for customization
html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>USAF Procurement Fraud Investigation Framework (PFIF)</title>
  <style>
    /* === GLOBAL STYLES === */
    body {
      font-family: Roboto, sans-serif;
      background: #f4f4f4;
      margin: 0;
      padding: 0;
    }
    .header-date {
      font-size: 0.9em;
      color: #cccccc;
      margin-left: 1em;
    }

    /* === HEADER STYLING === */
header {
  background-color: #003366;
  color: white;
  padding: 1em;
}

/* New flex container for header layout */
.header-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap; /* for smaller screens */
}

.header-title {
  font-size: 1.5em;
  flex: 2;
  text-align: center
}

.header-date {
  font-size: 0.9em;
  color: #FFFFFF;
  flex: 1;
  padding-left: 1em;
  font-style: italic;
}

.header-contact {
  flex: 1;
  text-align: right;
}

.header-contact a {
  color: #4B9CD3;
  text-decoration: underline;
  font-size: 0.95em;
}

    /* === TREE CONTAINER === */
    #tree-container {
      margin: 2em;                /* Adjust spacing around tree */
    }

 /* === TOOLTIP STYLING === */
.tooltip {
  position: absolute;
  background-color: #fff;
  border: 1px solid #ccc;
  padding: 5px 8px;
  font-size: 12px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.2s;

  /* Added for better readability and wrapping */
  max-width: 300px;           /* Optional: limit width */
  white-space: normal;        /* Enables wrapping */
  word-wrap: break-word;      /* Break long words if needed */
  line-height: 1.4;           /* Improve line spacing */
  border-radius: 4px;         /* Optional: rounded corners */
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15); /* Optional: subtle shadow */
}

  </style>
</head>
<body>
  
  <!-- === PAGE HEADER === -->
<header>
  <div class="header-container">
    <div class="header-date">Data as of: May 9, 2025</div>
    <div class="header-title">Procurement Fraud Investigation Framework (PFIF)</div>
    
    <div class="header-contact">
      <a href="mailto:john.murray.36@us.af.mil?subject=PFIF%20Update&body=Resource%20Name:%0ADescription%20of%20Tool:%0AURL:">
        Email an Addition
      </a>
    </div>
  </div>
</header>

<div style="padding-left: 20px; margin-top: 10px; font-size: 14px;">
  <p><strong>Legend:<br></strong> Click nodes to expand. <br>Tooltip appears on hover. <br> Click leaf nodes to open resource link. <br>Cost (c) Public (p) PKI (i)
</div>
  <!-- === TOOLTIP CONTAINER === -->
  <div id="tooltip" class="tooltip"></div>

  <!-- === TREE SVG CONTAINER === -->
  <svg id="tree-container"></svg>

  <!-- === D3 LIBRARY === -->
  <script src="https://d3js.org/d3.v7.min.js"></script>

  <script>
    // === INSERTED JSON TREE STRUCTURE ===
    const data = <<TREE_JSON>>;

    // === TREE CONFIGURATION ===
    const width = 960;
    const dx = 30;                // Vertical spacing between nodes
    const dy = width / 4;         // Horizontal spacing between levels

    const tree = d3.tree().nodeSize([dx, dy]);
    const diagonal = d3.linkHorizontal().x(d => d.y).y(d => d.x);

    // === BUILD ROOT FROM DATA ===
    const root = d3.hierarchy(data);
    root.x0 = dy / 2;
    root.y0 = 0;
    root.descendants().forEach((d, i) => {
    d.id = i;
    d._children = d.children;
    if (d.depth > 0) d.children = null; // collapse all nodes except root
    });

    // === SVG SETUP ===
// === SVG SETUP WITH ZOOM ===
const svg = d3.select("#tree-container")
  .attr("viewBox", [-dy / 3, -dx * 10, width, 600])
  .style("font", "10px sans-serif")
  .style("user-select", "none");

// === Enable Zoom Behavior ===
svg.call(d3.zoom()
  .scaleExtent([0.1, 3])
  .on("zoom", (event) => {
    gZoom.attr("transform", event.transform);
  }));

// === Group for Zoomable Content ===
const gZoom = svg.append("g");
const gLink = gZoom.append("g")
  .attr("fill", "none")
  .attr("stroke", "#4B9CD3")   // Line color between nodes
  .attr("stroke-opacity", 0.4)
  .attr("stroke-width", 1.5);
const gNode = gZoom.append("g")
  .attr("cursor", "pointer")
  .attr("pointer-events", "all");

    const tooltip = d3.select("#tooltip");

    // === MAIN UPDATE FUNCTION ===
    function update(source) {
      const duration = 250;
      const nodes = root.descendants().reverse();
      const links = root.links();

      tree(root);

// === CENTER ON FURTHEST RIGHT NODE ===
const rightmost = root.descendants().reduce((a, b) => a.y > b.y ? a : b);
svg.call(
  d3.zoom().transform,
  d3.zoomIdentity.translate(width / 2 - rightmost.y, 0)
);

      const transition = svg.transition().duration(duration)
        .attr("viewBox", [-dy / 3, -dx * 10, width, dx * 20]) // Set an initial guess height; will be overwritten by `update()`


      // === NODE JOIN ===
      const node = gNode.selectAll("g").data(nodes, d => d.id);

      // === NEW NODES ENTER ===
      const nodeEnter = node.enter().append("g")
        .attr("transform", d => `translate(${source.y0},${source.x0})`)
        .on("click", (event, d) => {
          if (d.data.url && !d.children && !d._children) {
            window.open(d.data.url, "_blank");  // Open links in new tab
          } else {
            d.children = d.children ? null : d._children;
            update(d);  // Toggle children
          }
        })
        .on("mouseover", (event, d) => {
          tooltip.html(d.data.tooltip || d.data.name)  // Tooltip logic
            .style("left", `${event.pageX + 10}px`)
            .style("top", `${event.pageY}px`)
            .style("opacity", 1);
        })
        .on("mouseout", () => tooltip.style("opacity", 0));

      // === CIRCLE STYLE ===
      nodeEnter.append("circle")
        .attr("r", 4)                     // Radius of nodes
        .attr("fill", d => d._children ? "#00308F" : "#00205B");  // Collapsed = darker

      // === TEXT STYLE ===
      nodeEnter.append("text")
        .attr("dy", "-0.37em") // vertical alignment
        .attr("x", d => d._children ? -6 : 6) // horizontal offset from the node
        .attr("text-anchor", d => d._children ? "end" : "start") // text alignment
        .text(d => d.data.name)
        .clone(true).lower()
        .attr("stroke", "white");        // Outline for better contrast

      // === NODE UPDATE TRANSITION ===
      node.merge(nodeEnter).transition(transition)
        .attr("transform", d => `translate(${d.y},${d.x})`);

      // === NODE EXIT TRANSITION ===
      node.exit().transition(transition).remove()
        .attr("transform", d => `translate(${source.y},${source.x})`)
        .attr("opacity", 0);

      // === LINK JOIN ===
      const link = gLink.selectAll("path").data(links, d => d.target.id);

      // === NEW LINKS ===
      const linkEnter = link.enter().append("path")
        .attr("d", d => {
          const o = d.source.depth === 0
            ? { x: d.source.x, y: d.source.y + 40 }  // Offset root link
            : d.source;
          return diagonal({ source: o, target: d.target });
        });

      // === LINK TRANSITIONS ===
      link.merge(linkEnter).transition(transition).attr("d", diagonal);
      link.exit().transition(transition).remove()
        .attr("d", d => {
          const o = { x: source.x, y: source.y };
          return diagonal({ source: o, target: o });
        });

      // Update saved positions
      root.eachBefore(d => {
        d.x0 = d.x;
        d.y0 = d.y;
      });
    }

    // === INITIAL DRAW ===
    update(root);
  </script>
</body>
</html>
"""


# In[15]:


# Convert tree to JSON string and embed into HTML
tree_json = json.dumps(final_tree, indent=2)
final_html = html_template.replace("<<TREE_JSON>>", tree_json)

# Save to the same directory as the input CSV
output_path = os.path.join(os.path.dirname(csv_path), "USAF_PFIF_tree.html")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(final_html)

print(f"✅ HTML file created:\n{output_path}")
