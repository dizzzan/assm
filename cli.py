#!/usr/bin/env python3

import click
import yaml
import json
import boto3
import os
import sys
from pathlib import Path

CLI = "assm"
NAME = "Another Simple Secrets Manager"
CONFIG_FILE = f".{CLI}-config.yml"

_client: boto3.client


@click.group(
    help=f"{NAME} ({CLI}) seeds environment variables using secrets from AWS Secrets Manager."
)
def cli():
    pass


@cli.command(
    help="Seed secrets into environment variables.",
    context_settings={"show_default": True},
)
@click.option(
    "-f",
    "--file",
    help=f"File name containing configuration.",
    default=CONFIG_FILE,
)
@click.option(
    "-t",
    "--traverse",
    help=f"Traverse up from CWD looking for configs.",
    default=False,
    is_flag=True,
)
def seed(file, traverse):
    configs = load_configs(file, traverse)
    if configs:
        load_secrets(configs)
    else:
        raise FileNotFoundError("No configs found!")


@cli.command(
    help="Unset all environments set by seed.\n WARNING: This might unset variables set by other means!",
    context_settings={"show_default": True},
)
@click.option(
    "-f",
    "--file",
    help=f"File name containing configuration.",
    default=CONFIG_FILE,
)
@click.option(
    "-t",
    "--traverse",
    help=f"Traverse up from CWD looking for configs.",
    default=False,
    is_flag=True,
)
def wipe(file, traverse):
    configs = load_configs(file, traverse)
    wipe_secrets(configs)


def load_configs(file, traverse):
    configs = []
    if traverse:
        dir = Path(os.getcwd())
        while True:
            sf = Path(dir) / CONFIG_FILE
            if sf.exists():
                configs.append(str(sf))
            if dir == Path(os.sep):
                break
            dir = dir.parent.absolute()
    else:
        if Path(file).exists():
            configs.append(file)
    return configs


def wipe_secrets(configs):
    for cfg_filename in configs:
        with open(cfg_filename) as cfg_file:
            cfg = yaml.safe_load(cfg_file)
            for sec in cfg.get("secrets"):
                print(f" unset {sec.get('env')}")


def load_secrets(configs):
    for cfg_filename in configs:
        with open(cfg_filename) as cfg_file:
            cfg = yaml.safe_load(cfg_file)
            aws_profile = cfg.get("config").get(
                "aws_profile", os.environ["AWS_PROFILE"]
            )
            session = boto3.Session(profile_name=aws_profile)
            _client = session.client("secretsmanager")
            print(
                # f" # Loading secrets found in '{cfg_filename}' from AWS[{aws_profile}]"
            )
            for sec in cfg.get("secrets"):
                id = sec.get("id")
                key = sec.get("key")
                env = sec.get("env")
                if not env:
                    print(f" # !!! No env var specified for secret {id}")
                    continue
                try:
                    asm_response = _client.get_secret_value(SecretId=id)
                    secret_value = asm_response["SecretString"]
                except Exception as e:
                    print(f"# !!! Cound not load secret {id}: {e}")
                    continue
                if key:
                    secret_value = json.loads(secret_value).get(key)
                print(f" # {id}:{key} -> {env}")
                print(f" export {env}={secret_value}")


@cli.command(help="Print a sample config file.")
def sample():
    print(
        yaml.dump(
            {
                "config": {
                    "aws_profile": "default",
                },
                "secrets": [
                    {"id": "my-secret-id", "key": "password", "env": "MY_SECRET"}
                ],
            },
            indent=2,
        )
    )


@cli.command(help="Generate some useful shell aliases.")
def alias():
    f = __file__
    c = sys.argv[0]
    tmpl = f"assmf() {{ eval `{c} %%` }};assmf"
    include_cli_alias = f'alias {CLI}="python ' + f + '"' if c != CLI else ""
    print(
        f"""
# Add these to your .bashrc or .zshrc 
# Warning! eval can be dangerous, use at your own risk!
{include_cli_alias}
alias {CLI}s="{(tmpl.replace("%%", "seed -t"))}"
alias {CLI}w="{(tmpl.replace("%%", "wipe -t"))}"
"""
    )


if __name__ == "__main__":
    cli()