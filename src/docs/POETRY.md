# Install poetry
```bash
curl -sSL https://install.python-poetry.org | python3 -

echo 'export PATH="/Users/rongrong/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

poetry --version

# Config poetry
```poetry config --list```

set the virtual environment to be created in the project directory (this makes it easier to find and manage):
```poetry config virtualenvs.in-project true```


# install dependency
```poetry install```


# check virtual environment info
poetry env info


# virtual environemnt
Two Options
1. Activate the virtual environments
```bash
poetry env activate
$ eval $(poetry env activate)
(test-project-for-test) $  # Virtualenv entered
```

remember to type ```deactivate``` to exit the virtual environment.
After running deactivate, your prompt should return to normal without the ssat-py3.13 prefix. You can verify this by running ```poetry env list``` again.

2. Run project
```poetry run python src/main.py```