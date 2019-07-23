# inspectmodule
  Python script to list classes, functions and modules used in a py file
  
  The script prints a list of all imported modules, all classes and functions defined inside the file, and all data variables that store a function return value or instance of a class.

## Usage
  1) Import inspectmodule as a module
  2) Use the inspectAt method to inspect a python file

# Limitations
  The type of the data variables is not listed because it cannot be determined without executing the file
  It is assumed that all imported modules are either provided or available on pip
