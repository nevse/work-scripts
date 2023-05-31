# work-scripts

Release can be found here https://test.pypi.org/project/project-conv-nevse/

## Install csrpoj packagereference converter
```
pip3 install -i https://test.pypi.org/simple/ project-conv-nevse
```

To update package use this command
```
pip3 install --upgrade -i https://test.pypi.org/simple/ project-conv-nevse
```

## How to use
Type `conv` in directory wich contains project solution. Don't type it in work or other folder witch contains several projects!!! It will convert all of them.

## Problems

On `macos` it might be a problem to run command `conv` from console. In this case you should setup an alias in .zshrc or .bashrc. For example:
```
alias conv="python3 -m conv_package"
```
