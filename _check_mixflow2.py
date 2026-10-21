import sys
mods=["numpy","scipy"]
for m in mods:
    try:
        mod=__import__(m); print("OK",m,getattr(mod,"__version__",""))
    except Exception as e: print("FAIL",m,e)
print("Python",sys.version)
