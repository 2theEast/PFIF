<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Procurement Fraud Resource Tree</title>
  <style>
    body { font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 0; }
    header { background-color: #003366; color: white; padding: 1em; text-align: center; }
    header a { color: #00ffff; text-decoration: underline; }
    #tree-container { margin: 2em; }
    .last-updated { font-size: 0.9em; margin-top: 0.5em; color: #ccc; }
    .node { cursor: pointer; }
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
  <header><h1>Procurement Fraud Investigation Framework</h1></header>
  <div class="legend"><strong>Legend:</strong> Canonical categories & tools</div>
  <svg id="tree-container"></svg>
  <div id="tooltip" class="tooltip"></div>
  <script src="https://d3js.org/d3.v7.min.js"></script>
  <script>
    // Placeholder for dynamic data
    const data = {/* Tree data structure goes here */};

    const width = 960;
    const dx = 30;
    const dy = width / 4;
    const tree = d3.tree().nodeSize([dx, dy]);
    const diagonal = d3.linkHorizontal().x(d => d.y).y(d => d.x);
    const root = d3.hierarchy(data);
    root.x0 = dy / 2;
    root.y0 = 0;
    root.descendants().forEach((d, i) => {
      d.id = i;
      d._children = d.children;
      if (d.depth && d.data.name.length !== 7) d.children = null;
    });

    const svg = d3.select("#tree-container")
      .attr("viewBox", [-dy / 3, -dx * 10, width, 600])
      .style("font", "10px sans-serif")
      .style("user-select", "none");

    const gLink = svg.append("g")
      .attr("fill", "none")
      .attr("stroke", "#555")
      .attr("stroke-opacity", 0.4)
      .attr("stroke-width", 1.5);

    const gNode = svg.append("g")
      .attr("cursor", "pointer")
      .attr("pointer-events", "all");

    const tooltip = d3.select("#tooltip");

    function update(source) {
      const duration = 250;
      const nodes = root.descendants().reverse();
      const links = root.links();

      tree(root);

      let left = root;
      let right = root;
      root.eachBefore(node => {
        if (node.x < left.x) left = node;
        if (node.x > right.x) right = node;
      });

      const transition = svg.transition().duration(duration)
        .attr("viewBox", [-dy / 3, left.x - dx * 2, width, right.x - left.x + dx * 4]);

      const node = gNode.selectAll("g").data(nodes, d => d.id);

      const nodeEnter = node.enter().append("g")
        .attr("transform", d => `translate(${source.y0},${source.x0})`)
        .on("click", (event, d) => {
          if (d.data.url && !d.children && !d._children) {
            window.open(d.data.url, "_blank");
          } else {
            d.children = d.children ? null : d._children;
            update(d);
          }
        })
        .on("mouseover", (event, d) => {
          tooltip.html(d.data.tooltip || d.data.name)
            .style("left", `${event.pageX + 10}px`)
            .style("top", `${event.pageY}px`)
            .style("opacity", 1);
        })
        .on("mouseout", () => tooltip.style("opacity", 0));

      nodeEnter.append("circle")
        .attr("r", 4)
        .attr("fill", d => d._children ? "#555" : "#999");

      nodeEnter.append("text")
        .attr("dy", "0.31em")
        .attr("x", d => d._children ? -6 : 6)
        .attr("text-anchor", d => d._children ? "end" : "start")
        .text(d => d.data.name)
        .clone(true).lower()
        .attr("stroke", "white");

      node.merge(nodeEnter).transition(transition)
        .attr("transform", d => `translate(${d.y},${d.x})`);

      node.exit().transition(transition).remove()
        .attr("transform", d => `translate(${source.y},${source.x})`)
        .attr("opacity", 0);

      const link = gLink.selectAll("path").data(links, d => d.target.id);

      const linkEnter = link.enter().append("path")
        .attr("d", d => {
          const o = d.source.depth === 0
            ? { x: d.source.x, y: d.source.y + 40 }
            : d.source;
          return diagonal({ source: o, target: d.target });
        });

      link.merge(linkEnter).transition(transition).attr("d", diagonal);

      link.exit().transition(transition).remove()
        .attr("d", d => {
          const o = { x: source.x, y: source.y };
          return diagonal({ source: o, target: o });
        });

      root.eachBefore(d => {
        d.x0 = d.x;
        d.y0 = d.y;
      });
    }

    update(root);
  </script>
</body>
</html>
