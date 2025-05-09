#!/usr/bin/env python
# coding: utf-8

# In[ ]:


"C:/Users/MapaM/OneDrive/osint-fraud-framework/USAF_PFIF_Tree.csv"


# In[2]:


import os
import json
import pandas as pd
from urllib.parse import urlparse

csv_path = "C:/Users/MapaM/OneDrive/osint-fraud-framework/USAF_PFIF_Tree.csv"

# Step 1: Load the raw CSV file
df = pd.read_csv(csv_path)

# Step 2: Clean all column headers by stripping whitespace and converting to lowercase
df.columns = df.columns.str.strip().str.lower()

# Step 3: Preview the headers to confirm cleanup
print("Cleaned column headers:", df.columns.tolist())

# Step 4: Clean the 'url' field by extracting the base domain only
def sanitize_url(url):
    if not isinstance(url, str) or url.strip() == "" or url.lower() in ["nan", "none"]:
        return "Unavailable"
    try:
        parsed = urlparse(url)
        return parsed.netloc if parsed.netloc else "Unavailable"
    except Exception:
        return "Unavailable"

# Step 5: Apply the cleaning to a new column
df["clean_url"] = df["url"].apply(sanitize_url)

# Step 6: Preview a few records
df.head()


# In[3]:


print("Available columns after cleaning:", df.columns.tolist())


# In[4]:


# Step 1: Check for missing or unexpected values
print("Unique Parent Categories:\n", df['parent'].value_counts(), "\n")
print("Unique Child Categories:\n", df['child'].value_counts(), "\n")

# Only try subchild if it exists
if "subchild" in df.columns:
    print("Unique Subchild Names:\n", df['subchild'].value_counts(), "\n")
else:
    print("No 'subchild' column found. Proceeding without it.\n")

# Step 2: Fill missing values only for columns that exist
for col in ['parent', 'child', 'subchild']:
    if col in df.columns:
        df[col].fillna("Unknown", inplace=True)
# Step 3: Build hierarchical tree for D3.js with multiple top-level parents
def build_tree(df):
    root = {"name": "PFIF", "children": []}  # Neutral root
    parent_dict = {}

    for _, row in df.iterrows():
        p = row["parent"]
        c = row["child"]
        s = row["subchild"] if "subchild" in df.columns else None
        r = row["resource_name"]
        tooltip = row.get("tooltip", "")
        url = row.get("clean_url", "Unavailable")

        # Add parent node
        if p not in parent_dict:
            parent_node = {"name": p, "children": []}
            parent_dict[p] = parent_node
            root["children"].append(parent_node)
        else:
            parent_node = parent_dict[p]

        # Add child node
        child_node = next((item for item in parent_node["children"] if item["name"] == c), None)
        if not child_node:
            child_node = {"name": c, "children": []}
            parent_node["children"].append(child_node)

        # Optional: Add subchild if it exists
        if s and s != r:
            subchild_node = {"name": s, "children": [{
                "name": r,
                "tooltip": tooltip,
                "url": url
            }]}
            child_node["children"].append(subchild_node)
        else:
            resource_node = {
                "name": r,
                "tooltip": tooltip,
                "url": url
            }
            child_node["children"].append(resource_node)

    return root


# Step 4: Build the tree
tree_data = build_tree(df)

# Step 5: Save cleaned hierarchical JSON
with open("cleaned_pfif_tree.json", "w") as f:
    json.dump(tree_data, f, indent=2)

# Optional: Preview JSON output
print(json.dumps(tree_data, indent=2)[:1000])



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


# In[39]:


# Build hierarchical structure for D3.js with proper field usage
def build_tree_from_df(df):
    # Root of the tree
    root = {"name": "Start Here", "children": []}  # or "Root" or "Procurement Fraud Investigation Framework"
    parent_dict = {}

    for _, row in df.iterrows():
        p = row["parent"]
        c = row["child"]
        s = row.get("subchild", "")  # Optional 3rd level
        resource = row["resource_name"]
        tooltip = row.get("tooltip", "")
        url = row.get("clean_url", "Unavailable")

        # Create parent node if not exists
        if p not in parent_dict:
            parent_node = {"name": p, "children": []}
            parent_dict[p] = parent_node
            root["children"].append(parent_node)
        else:
            parent_node = parent_dict[p]

        # Get or create child under parent
        child_node = next((item for item in parent_node["children"] if item["name"] == c), None)
        if not child_node:
            child_node = {"name": c, "children": []}
            parent_node["children"].append(child_node)

        # Get or create subchild under child (optional level)
        if s:
            sub_node = next((item for item in child_node["children"] if item["name"] == s), None)
            if not sub_node:
                sub_node = {"name": s, "children": []}
                child_node["children"].append(sub_node)
        else:
            sub_node = child_node

        # Append the resource node to the correct level
        resource_node = {
            "name": resource,
            "tooltip": tooltip,
            "url": url
        }
        sub_node["children"].append(resource_node)

    return root


# Build the tree from the cleaned DataFrame
tree_data = build_tree_from_df(df)

# Save to JSON file
with open("cleaned_pfif_tree.json", "w") as f:
    json.dump(tree_data, f, indent=2)

# Optional preview
print(json.dumps(tree_data, indent=2)[:1000])


# In[40]:


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


# In[45]:


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
      padding: 5px;
      font-size: 12px;
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.2s;
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

      // Customize this filter to collapse nodes based on logic
      if (d.depth && d.data.name.length !== 7) d.children = null;
    });

    // === SVG SETUP ===
    const svg = d3.select("#tree-container")
      .attr("viewBox", [-dy / 3, -dx * 10, width, 600]) // Adjust view box to fit content
      .style("font", "10px sans-serif")
      .style("user-select", "none");

    // === LINK GROUP ===
    const gLink = svg.append("g")
      .attr("fill", "none")
      .attr("stroke", "#4B9CD3")             // Line color between nodes
      .attr("stroke-opacity", 0.4)
      .attr("stroke-width", 1.5);

    // === NODE GROUP ===
    const gNode = svg.append("g")
      .attr("cursor", "pointer")
      .attr("pointer-events", "all");

    const tooltip = d3.select("#tooltip");

    // === MAIN UPDATE FUNCTION ===
    function update(source) {
      const duration = 250;
      const nodes = root.descendants().reverse();
      const links = root.links();

      tree(root);

      // === DYNAMIC TREE HEIGHT ===
      let left = root, right = root;
      root.eachBefore(node => {
        if (node.x < left.x) left = node;
        if (node.x > right.x) right = node;
      });

      const transition = svg.transition().duration(duration)
        .attr("viewBox", [-dy / 3, left.x - dx * 2, width, right.x - left.x + dx * 4]);

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


# In[46]:


# Convert tree to JSON string and embed into HTML
tree_json = json.dumps(tree_data, indent=2)
final_html = html_template.replace("<<TREE_JSON>>", tree_json)

# Save to the same directory as the input CSV
output_path = os.path.join(os.path.dirname(csv_path), "USAF_PFIF_tree.html")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(final_html)

print(f"✅ HTML file created:\n{output_path}")



# In[1]:


import os
os.getcwd()


# In[ ]:




