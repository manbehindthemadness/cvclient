# -*- coding: UTF-8 -*-
"""
This file is part of the cvclient package.
Copyright (c) 2021 Kevin Eales.
------------------------------------------------------------------------------------------------------------------------
Loggers and general utilities.
"""
import os
import logging


WORKING_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
logging.getLogger().setLevel(logging.INFO)


def clean_args(args: list, kwargs: dict, exclusive: bool = False) -> dict:
    """
    Removes keys top prevent errors.
    """
    kargs = list(kwargs.keys())
    if exclusive:
        for arg in kargs:
            if arg not in args:
                del kwargs[arg]
    else:
        for arg in args:
            try:
                del kwargs[arg]
            except KeyError:
                pass
    return kwargs


def get_args(args: list, kwargs: dict, clean: bool = False) -> list:
    """
    This will fetch arguments and jazz.
    """
    values = list()
    for arg in args:
        if arg in kwargs:
            values.append(kwargs[arg])
        else:
            values.append(None)
    if clean:
        clean_args(args, kwargs)
    if len(values) == 1:
        values = values[0]
    return values


def log(*args, **kwargs):
    """
    Really simple-ass logger.
    """

    message = str()
    for arg in args:
        message += str(arg) + ' '
    level = get_args(
        ['level'],
        kwargs
    )
    if not level:
        level = 'info'
    cmd = 'logging.' + level + '(message)'
    exec(cmd)
