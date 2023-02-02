# rov-timing-code

## Installation

Install python dependencies:
```
pip install -r requirements.txt
```

And selenium dependencies on your system:
- geckodriver
- Xvfb (xorg-server-xvfb on archlinux)

## Configuration

Make sure credentials and IP resources are set in config.json files. See
config.json.example for the file format.

## Creating a ROA
Example for APNIC resources:

```zsh
cd src/apnic
python bot.py create 103.171.218.0/24 3970 24
```

## Deleting a ROA
Example for APNIC resources:

```zsh
cd src/apnic
python bot.py delete 103.171.218.0/24 3970 
```

## Get TOTP security token

```zsh
cd src/apnic
python bot.py token
```

