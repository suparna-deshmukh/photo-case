import ast, builtins
src = open("space_jog/app.py").read()
tree = ast.parse(src)
defined = set(dir(builtins))
for node in ast.walk(tree):
    if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
        defined.add(node.id)
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
        if hasattr(node, "name") and node.name: defined.add(node.name)
        for a in getattr(node, "args", []).args + getattr(node, "args", []).kwonlyargs + getattr(node, "args", []).posonlyargs:
            defined.add(a.arg)
        if getattr(node, "args", []).vararg: defined.add(node.args.vararg.arg)
        if getattr(node, "args", []).kwarg: defined.add(node.args.kwarg.arg)
    elif isinstance(node, (ast.Import, ast.ImportFrom)):
        for a in node.names:
            defined.add((a.asname or a.name).split(".")[0])
    elif isinstance(node, ast.comprehension):
        for n in ast.walk(node.target):
            if isinstance(n, ast.Name): defined.add(n.id)
    elif isinstance(node, ast.ExceptHandler) and node.name:
        defined.add(node.name)
    elif isinstance(node, ast.arg):
        defined.add(node.arg)
hits = {}
for node in ast.walk(tree):
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
        if node.id not in defined:
            hits.setdefault(node.id, node.lineno)
for k, v in sorted(hits.items(), key=lambda kv: kv[1]):
    print(f"line {v}: {k}")
print("--- done")
