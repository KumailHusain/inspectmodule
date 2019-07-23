import ast
import _ast
import json
import importlib
import getmodules
import inspect

# Result dict/json
details = {}
# Holds instances to dynamically imported modules
importInstances = {}

# SCAN FUNCTIONS START HERE

def _hasName(object):
    # Does object have a __name__ attribute
    if inspect.ismethod(object) or \
        inspect.isclass(object) or \
        inspect.isfunction(object) or \
        inspect.isgenerator(object) or \
        inspect.iscoroutine(object) or \
        inspect.isbuiltin(object):
        return True
    return False


def _populateInstances():
    global details

    for item in details['Imports']:
        name = item.split(' ')[0]
        try:
            importInstances[name] = importlib.import_module(name)
        except ImportError as e:
            return False
    for item in details['Import From']:
        for i in details['Import From'][item]:
            name = i.split(' ')[0]
            try:
                mod = importlib.import_module(item + "." + name)
                importInstances[item + "." + name] = mod
            except ImportError:
                try:
                    mod = importlib.import_module(item)
                    met = getattr(mod, name)
                    importInstances[item + "." + name] = met
                except:
                    return False
    return True

def _addItem(resolvedName):
    global details
    global importInstances

    for key in importInstances:
        if resolvedName[:len(key)] == key:
            comps = resolvedName[len(key):].split('.')
            if comps[0] != '':
                return
            rootmember = importInstances[key]
            if key not in details['Scanned Items']:
                details['Scanned Items'][key] = {}
            scanDetails = details['Scanned Items'][key]
            for i in comps[1:]:
                members = inspect.getmembers(rootmember, _hasName)
                for name, value in members:
                    if value.__name__ == i:
                        if inspect.isclass(value):
                            if 'classes' not in scanDetails:
                                scanDetails['classes'] = {}
                            if value.__name__ not in scanDetails['classes']:
                                scanDetails['classes'][value.__name__] = {}
                            scanDetails = scanDetails['classes'][value.__name__]
                            rootmember = value
                        else:
                            if 'functions' not in scanDetails:
                                scanDetails['functions'] = {}
                            if value.__name__ not in scanDetails['functions']:
                                scanDetails['functions'][value.__name__] = {}
                            scanDetails = scanDetails['functions'][value.__name__]
                            rootmember = value
                        break

def _resolveName(func):
    if (type(func) == _ast.Name):
        return func.id
    elif (type(func) == _ast.Attribute):
        return _resolveName(func.value) + "." + func.attr
    else:
        return None

def _getAlias(item, aliasList):
    if type(item.value) != _ast.Call:
        return None
    resolvedName = _resolveName(item.value.func)
    for al, ac in aliasList:
        if resolvedName == al:
            return (item.targets[0].id, ac)
    return None

def _hasBody(item):
    if type(item) == _ast.FunctionDef or \
        type(item) == _ast.Module or \
        type(item) == _ast.ClassDef or \
        type(item) == _ast.For or \
        type(item) == _ast.While or \
        type(item) == _ast.If or \
        type(item) == _ast.With or \
        type(item) == _ast.Try:
        return True
    return False

def _scanUnknown(item, aliasList):
    global details
    if _hasBody(item):
        aliases = aliasList
        bodyItems = list(filter(_hasBody, item.body))
        for i in item.body:
            if i not in bodyItems:
                _scanUnknown(i, aliases)
        for i in bodyItems:
            _scanUnknown(i, aliases)
    elif type(item) == _ast.Import:
        for alias in item.names:
            if alias.asname == None:
                aliasList.append((alias.name, alias.name))
            else:
                aliasList.append((alias.asname, alias.name))
    elif type(item) == _ast.ImportFrom:
        for alias in item.names:
            if alias.asname == None:
                aliasList.append((alias.name, item.module + "." + alias.name))
            else:
                aliasList.append(alias.asname,
                                 item.module + "." + alias.name)
    elif type(item) == _ast.Assign:
        alias = _getAlias(item, aliasList)
        if (alias != None):
            aliasList.append(alias)
        else:
            _scanUnknown(item.value, aliasList)
        if type(item.value) == _ast.Call:
            if 'Data' not in details:
                details['Data'] = []
            
            name = ""
            if type(item.targets[0]) == _ast.Name:
                name = item.targets[0].id
            elif type(item.targets[0]) == _ast.Tuple:
                name = [i.id for i in item.targets[0].elts]
            if name not in details['Data']:
                details['Data'].append(name)
    elif type(item) == _ast.Expr:
        _scanUnknown(item.value, aliasList)
    elif type(item) == _ast.Call:
        resolvedName = _resolveName(item.func)
        for al, ac in aliasList:
            if resolvedName[:len(al)] == al:
                parts = resolvedName.split('.', 1)
                if parts[0] != al or len(parts) < 2:
                    continue
                name = ac + "." + parts[1]
                for i in details['Imports']:
                    if i in name[:len(i)]:
                        _addItem(name)
                for i in details['Import From']:
                    for j in details['Import From'][i]:
                        if i + "." + j in name[:len(i + "." + j)]:
                            _addItem(name)


def _getMissingPackages():
    global details
    # Returns True if all modules are importable

    packages = []
    for item in details['Imports']:
        packages.append(item.split(' ')[0])
    for item in details['Import From']:
        packages.append(item)
    getmodules.createReqFile(packages)
    if not getmodules.installRequirements():
        print("Failed to install dependancies")
        return False
    return True

# INSPECT FUNCTIONS START HERE

def _getFunctionInfo(functionDef):
    functionInfo = {}
    arguments = functionDef.args
    functionInfo['args'] = []
    for arg in arguments.args:
        functionInfo['args'].append(arg.arg)
    R = functionDef.body
    while len(R) > 0:
        thisItem = R.pop(0)
        if type(thisItem) == _ast.Return:
            if type(thisItem.value) == _ast.Name:
                functionInfo['return'] = thisItem.value.id
                break
            elif type(thisItem.value) == _ast.Str:
                functionInfo['return'] = thisItem.value.s
                break
        if _hasBody(thisItem) and not \
            (type(thisItem) == _ast.FunctionDef or \
            type(thisItem) == _ast.Module or \
            type(thisItem) == _ast.ClassDef):
            for item in thisItem.body:
                R.append(item)
    return functionInfo

def _inspectImport(item):
    global details
    global importInstances
    if 'Imports' not in details:
        details['Imports'] = []
        
    for alias in item.names:
        if alias.asname == None:
            details['Imports'].append(alias.name)
        else:
            details['Imports'].append(alias.name + " as " + alias.asname)

def _inspectImportFrom(item):
    global details
    if 'Import From' not in details:
        details['Import From'] = {}

    details['Import From'][item.module] = []
    for alias in item.names:
        if alias.asname == None:
            details['Import From'][item.module].append(alias.name)
        else:
            details['Import From'][item.module].append(alias.name + " as " +
                                                       alias.asname)

def _inspectFunction(functionDef):
    functionDetails = _getFunctionInfo(functionDef)
    body = functionDef.body
    functions = list(filter(lambda x: type(x) == _ast.FunctionDef, body))
    
    for item in functions:
        if 'functions' not in functionDetails:
            functionDetails['functions'] = {}
        functionDetails['functions'][item.name] = _inspectFunction(item)
    return functionDetails

def _inspectClass(classDef):
    classDetails = {}
    
    funcs = list(filter(lambda x: type(x) == _ast.FunctionDef, classDef.body))
    classes = list(filter(lambda x: type(x) == _ast.ClassDef, classDef.body))
    for item in funcs:
        if 'methods' not in classDetails:
            classDetails['methods'] = {}
        classDetails['methods'][item.name] = _inspectFunction(item)
    for item in classes:
        if 'subclasses' not in classDetails:
            classDetails['subclasses'] = {}
        classDetails['subclasses'][item.name] = _inspectClass(item)
    return classDetails

def _inspectUnknown(item):
    global details
    if type(item) == _ast.Module:
        body = item.body
        # Handle aliases before class and func def
        classesfunctions = list(filter(lambda x: type(x) == _ast.ClassDef or
                                       type(x) == _ast.FunctionDef, body))
        for i in body:
            if i in classesfunctions:
                continue
            _inspectUnknown(i) 
        for item in classesfunctions:
            _inspectUnknown(item)
    elif type(item) == _ast.Import:
        _inspectImport(item)
    elif type(item) == _ast.ImportFrom:
        _inspectImportFrom(item)
    elif type(item) == _ast.ClassDef:
        if 'Classes' not in details:
            details['Classes'] = {}
        
        details['Classes'][item.name] = _inspectClass(item)
    elif type(item) == _ast.FunctionDef:
        if 'Functions' not in details:
            details['Functions'] = {}
            
        details['Functions'][item.name] = _inspectFunction(item)


# INSPECT FUNCTIONS END HERE

def inspectAt(path):
    global details

    st = open(path).read()
    tree = ast.parse(st)
    
    _inspectUnknown(tree)
    if not _getMissingPackages():
        details['Scanned Items'] = "Failed to install dependancies"
        return json.dumps(details, indent=4)
    
    if not _populateInstances():
        details['Scanned Items'] = "Failed to import some dependancies"
        return json.dumps(details, indent=4)
    details['Scanned Items'] = {}
    _scanUnknown(tree, [])
    
    return json.dumps(details, indent=4)
