import ast, builtins
src = open("space_jog/app.py").read()
tree = ast.parse(src)
defined = set(dir(builtins))
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        defined.add(node.name)
    elif isinstance(node, ast.Assign):
        for t in node.targets:
            for n in ast.walk(t):
                if isinstance(n, ast.Name): defined.add(n.id)
    elif isinstance(node, ast.AnnAssign) and node.target:
        for n in ast.walk(node.target):
            if isinstance(n, ast.Name): defined.add(n.id)
    elif isinstance(node, (ast.Import, ast.ImportFrom)):
        for a in node.names:
            defined.add((a.asname or a.name).split(".")[0])
    elif isinstance(node, ast.Try):
        for h in node.handlers:
            if h.name: defined.add(h.name)
for node in ast.walk(tree):
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
        if node.id not in defined:
            print(f"line {node.lineno}: {node.id}")
    elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        pass
