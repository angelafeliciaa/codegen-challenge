import ast
import os
import networkx as nx
import plotly.graph_objects as go
from typing import Dict, Set, Tuple
import json

def parse_imports(file_path: str) -> Dict[str, Set[str]]:
    with open(file_path, 'r') as file:
        tree = ast.parse(file.read())

    imports = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.name] = {alias.name}
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for alias in node.names:
                full_name = f"{module}.{alias.name}" if module else alias.name
                imports[full_name] = {alias.name}

    return imports

def mark_dead_code(G: nx.DiGraph, file_nodes: Dict[str, str]):
    for file_node in file_nodes.values():
        if G.out_degree(file_node) == 0:
            G.nodes[file_node]['color'] = 'red'

def read_file_content(file_path: str) -> str:
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"
    
import json
import plotly.graph_objects as go
import networkx as nx
import os
import ast
from typing import Tuple, Dict

def get_function_code(node: ast.FunctionDef) -> str:
    return ast.unparse(node)

def get_class_code(node: ast.ClassDef) -> str:
    return ast.unparse(node)

def build_import_graph(directory: str) -> Tuple[nx.DiGraph, Dict[str, str], Dict[str, str]]:
    G = nx.DiGraph()
    file_nodes = {}
    function_codes = {}
    class_codes = {}

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                file_node = file_path
                G.add_node(file_node, color='blue', type='file')
                file_nodes[file_path] = file_node

                with open(file_path, 'r') as f:
                    tree = ast.parse(f.read())

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_name = f"{file_node}::{node.name}"
                        G.add_node(func_name, color='green', type='function')
                        G.add_edge(file_node, func_name)
                        function_codes[func_name] = get_function_code(node)
                    elif isinstance(node, ast.ClassDef):
                        class_name = f"{file_node}::{node.name}"
                        G.add_node(class_name, color='red', type='class')
                        G.add_edge(file_node, class_name)
                        class_codes[class_name] = get_class_code(node)
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                method_name = f"{class_name}::{item.name}"
                                G.add_node(method_name, color='green', type='function')
                                G.add_edge(class_name, method_name)
                                function_codes[method_name] = get_function_code(item)

                imports = parse_imports(file_path)
                for imported_module, symbols in imports.items():
                    G.add_node(imported_module, color='yellow', type='module')
                    G.add_edge(file_node, imported_module)

    return G, file_nodes, {**function_codes, **class_codes}

def create_interactive_graph(G: nx.DiGraph, function_codes: Dict[str, str], output_file: str):
    pos = nx.spring_layout(G, k=0.5, iterations=50)
    
    edge_trace = go.Scatter(
        x=[], y=[],
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines')

    node_trace = go.Scatter(
        x=[], y=[],
        mode='markers',
        hoverinfo='text',
        marker=dict(
            showscale=False,
            color=[],
            size=30,
            line_width=2))

    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_trace['x'] += (x0, x1, None)
        edge_trace['y'] += (y0, y1, None)

    node_colors = []
    node_text = []
    for node in G.nodes():
        x, y = pos[node]
        node_trace['x'] += (x,)
        node_trace['y'] += (y,)
        node_colors.append(G.nodes[node]['color'])
        node_text.append(f"{node}<br>Type: {G.nodes[node]['type']}")

    node_trace.marker.color = node_colors
    node_trace.text = node_text

    fig = go.Figure(data=[edge_trace, node_trace])

    fig.update_layout(
        title='',
        titlefont_size=20,
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20,l=5,r=5,t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='rgba(255,255,255,0.9)',
        paper_bgcolor='rgba(255,255,255,0.9)',
    )

    # Enhanced Code Preview
    preview_div = '''
    <div id="code-preview" style="position: fixed; top: 10px; right: 10px; width: 30%; height: 50%; 
                                  background-color: #f4f4f4; border: 1px solid #ccc; padding: 15px; 
                                  overflow: auto; display: none; box-shadow: 0px 0px 10px rgba(0,0,0,0.3); 
                                  border-radius: 8px;">
        <pre id="preview-content" style="font-family: monospace; white-space: pre-wrap; word-wrap: break-word;"></pre>
    </div>
    '''

    # Add click event for code preview
    fig.update_layout(
        clickmode='event+select'
    )

    # Add custom JavaScript for click event
    custom_js = '''
    <script>
document.addEventListener('DOMContentLoaded', function() {
    var previewDiv = document.getElementById('code-preview');

    // Function to close the preview box
    function closePreviewBox() {
        previewDiv.style.display = 'none';
    }

    // Event listener to close the preview box when clicking outside of it
    document.addEventListener('click', function(event) {
        if (!previewDiv.contains(event.target) && !document.getElementById('graph-div').contains(event.target)) {
            closePreviewBox();
        }
    });

    // Existing click event handler for Plotly graph
    var graphDiv = document.getElementById('graph-div');
    var functionCodes = %s;
    graphDiv.on('plotly_click', function(data) {
        var point = data.points[0];
        var nodeInfo = point.text.split('<br>');
        var nodeName = nodeInfo[0];
        var nodeType = nodeInfo[1].split(': ')[1];
        
        var previewContent = document.getElementById('preview-content');
        
        if (nodeType === 'function' || nodeType === 'class') {
            var code = functionCodes[nodeName];
            if (code) {
                previewContent.textContent = code;
                previewDiv.style.display = 'block';
            } else {
                previewContent.textContent = 'Code not available';
                previewDiv.style.display = 'block';
            }
        } else if (nodeType === 'file') {
            fetch('/get_file_content?path=' + encodeURIComponent(nodeName))
                .then(response => response.text())
                .then(content => {
                    previewContent.textContent = content;
                    previewDiv.style.display = 'block';
                });
        } else {
            previewContent.textContent = 'No preview available for ' + nodeType + ': ' + nodeName;
            previewDiv.style.display = 'block';
        }
    });
});
</script>
    ''' % json.dumps(function_codes)

    # Write HTML file
    with open(output_file, 'w') as f:
        f.write(f'''
        <html>
        <head>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    overflow: hidden;
                }}
                #graph-div {{
                    width: 100%;
                    height: 90vh;
                    margin: auto;
                }}
                .legend-container {{
                    position: absolute;
                    top: 10px;
                    left: 10px;
                    background-color: #fff;
                    border: 1px solid #ccc;
                    padding: 10px;
                    z-index: 1;
                    border-radius: 8px;
                    box-shadow: 0px 0px 10px rgba(0,0,0,0.3);
                }}
                .legend-item {{
                    margin-bottom: 5px;
                }}
                .legend-color {{
                    display: inline-block;
                    width: 20px;
                    height: 20px;
                    vertical-align: middle;
                    margin-right: 10px;
                }}
            </style>
        </head>
        <body>
            <div id="graph-div"></div>
            <div class="legend-container">
                <div class="legend-item"><div class="legend-color" style="background-color: blue;"></div>File Node</div>
                <div class="legend-item"><div class="legend-color" style="background-color: green;"></div>Function Node</div>
                <div class="legend-item"><div class="legend-color" style="background-color: red;"></div>Class Node</div>
                <div class="legend-item"><div class="legend-color" style="background-color: yellow;"></div>Module Node</div>
            </div>
            {preview_div}
            <script>
                var graphData = {fig.to_json()};
                Plotly.newPlot('graph-div', graphData.data, graphData.layout);
            </script>
            {custom_js}
        </body>
        </html>
        ''')

def main(directory: str, output_file: str):
    G, file_nodes, function_codes = build_import_graph(directory)
    create_interactive_graph(G, function_codes, output_file)
    print(f"Interactive import graph saved to {output_file}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python script.py <directory> <output_file.html>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])