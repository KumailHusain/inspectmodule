import os

def createReqFile(packages):
    file = open("requirements.txt", "w")
    duplicates = {}
    for item in packages:
        try:
            __import__(item)
        except ImportError as e:
            if e.name not in duplicates:
                file.write(e.name + "\n")
                duplicates[e.name] = 1
    file.close()
    
def installRequirements():
    os.system("pip3 install -r requirements.txt")
    file = open("requirements.txt", "r")
    packages = file.readlines()
    for item in packages:
        try:
            # Remove \n
            __import__(item[:-1])
        except ImportError as e:
            print("Failed to import " + e.name)
            file.close()
            return False
    file.close()
    return True