# Copyright (c) 2017 SUSE LLC

import logging
import os
import shutil
import sys

import stagelib.git as git

COPY_LOGTEXT = '      {:<82}  -> {:1}'
PARENTHETICAL_LOGTEXT = '        {:<80}     {}'


def IOOSErrorGracefulFail(io_os_error, message):
    """
    Given an IOError or OSError exception, print the message to stdout, and then print relevant
    stats about the exception to stdout before exiting with error code 1.
    """
    o = io_os_error
    sys.stderr.write(f'{message}\n')
    # errno and strerror are common to IOError and OSError
    sys.stderr.write(f'Error [{o.errno}]: {o.strerror}\n')
    sys.exit(1)


def save_text_to_file(text, file_path):
    """Save text to a file at the file path. Will overwrite an existing file at the same path."""
    try:
        with open(file_path, 'w') as f:
            f.write(text)
    except (OSError, IOError) as o:
        IOOSErrorGracefulFail(o, f"Could not write text to file: {file_path}")


# List only files in dir
def list_files(path):
    """ List all files in the path non-recursively. Do not list dirs."""
    return [f for f in os.listdir(path)
            if os.path.isfile(os.path.join(path, f))]


def mkdir_if_dne(path, mode=0o755):
    """Make a directory if it does not exist"""
    if not os.path.isdir(path):
        try:
            os.mkdir(path, mode)
        except (OSError, IOError) as o:
            IOOSErrorGracefulFail(o, f"Could not create directory: {path}")


# Copy file from src to dst
def _copy_file(file_path, dst_path):
    try:
        shutil.copy2(file_path, dst_path)
    except (OSError, IOError) as o:
        IOOSErrorGracefulFail(o, f"Could not copy file {file_path} to {dst_path}")


def copy_files(filenames, src_path, dst_path, files_copied={}):
    """
    Copy a list of filenames from src to dst. Will overwrite existing files.
    For every copy made, make or update an entry in `files_copied`.
    """
    # Adding a trailing "/" if needed to improve output coherency
    dst_path = os.path.join(dst_path, '')
    mkdir_if_dne(dst_path)
    for f in filenames:
        file_path = os.path.join(src_path, f)
        dirty_marker = '*' if git.file_is_dirty(file_path) else ' '
        logging.info(COPY_LOGTEXT.format(f'{dirty_marker} {file_path}', dst_path))
        files_copied[os.path.join(dst_path, f)] = f'{dirty_marker} {file_path}'
        _copy_file(file_path, dst_path)


def recursive_copy_dir(src_path, dst_path, files_copied={}):
    """
    Copy all files in the src directory recursively to dst. Will overwrite existing files.
    For every copy made, make or update an entry in `files_copied`.
    """
    if not os.path.isdir(src_path):
        return
    for dirname, subdirs, files in os.walk(src_path, topdown=True):
        # Remove src_path (and '/' immediately following) from our dirname
        dst_path_offset = dirname[len(src_path) + 1:]
        copy_files(filenames=files, src_path=dirname,
                   dst_path=os.path.join(dst_path, dst_path_offset),
                   files_copied=files_copied)


def save_files_copied(files_copied, save_filename, strip_prefix=' '):
    """
    Given a dict of files that have been copied in the form {dst: src}, write a list of all files
    and their sources to the file. Optionally, a common prefix can be removed from the dst files.
    """
    printfmt = '{:<80}  <- {}\n'
    src_key = '  <source file> (preceding * indicates file is modified in git without a commit)'
    separator = '-' * (85 + len(src_key)) + '\n'
    filetext = separator
    filetext += f'Source version info:  repo [{git.get_repo()}] - branch [{git.get_branch()}] - commit hash [{git.get_hash()}]\n\n'

    filetext += printfmt.format('<staged file>', src_key)
    filetext += separator
    staged_paths = sorted(list(files_copied.keys()))
    for staged_path in staged_paths:
        staged_file = staged_path
        if staged_file.startswith(strip_prefix):
            staged_file = staged_file[len(strip_prefix):]
        filetext += printfmt.format(staged_file, files_copied[staged_path])
    save_text_to_file(filetext, save_filename)
