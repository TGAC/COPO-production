# Aspera Command-line Client Application

## Overview

The "aspera" command is a client application which allows you 
to interact with an Aspera Shares, Faspex or Files from the command line.

## Installation

Installation is accomplished by means of a "shell script" on Linux and
MacOS.

On Windows, just extract the self-contained .zip file that
contains all the binaries and support files into a directory of your choosing.
It will then be necessary to add the "bin" directory in that archive to
the PATH in order to be able to execute the "aspera" command from any
directory within a CMD window.

## Usage

By just typing the "aspera" command by itself, help text will be shown:

**Usage**

	aspera <command> [<args>]
	
**Commands**

	  faspex  use the Faspex application
	  files   use the Files application
	  help    view help for a specific command
	  shares  use the Shares application
	
**Examples**

	aspera help <command>

for extended help on the comand
	
    aspera <command> help <sub-command>

i.e., "aspera faspex help send" for options to send faspex packages

Subsequent commands like 'aspera help shares' will reveal sub-commands usage.
 
Complete command-line documentation is available on the Aspera Developer Network
website, and in the included "man" page for Linux.

## Additional Usage Notes

If an environment variable named ASPERA_PASS is set, the value of it
will be used as the password for all commands (if the password argument is not
passed to the command.)  Note that in Windows PowerShell, you will need to use

$env:ASPERA_PASS = "password"

To set the environment variable, as opposed to the usual "set" command.

### A few options deserve special attention:

You may specify multiple faspex package recipients by specifying the -r 
option multiple times.

Similarly, it is possible to specify the faspex send -f option multiple times.

All operations currently perform certificate validation. If a faspex, shares
or node server does not have a valid certificate in order to allow the
operation, please specify the --insecure option (not recommended in production.)

For sending (uploading) or getting (downloading) faspex packages, there are
options which may allow you to over-ride the default transfer speed settings
specified by the server or "faspe://" URL.  They are --min-rate, --target-rate
--rate-policy and --cipher.

There is a configuration file named ".aspera_cli_conf" in the aspera executable
directory that includes sample configurations that you can use as a reference.  
This file is used to specify credentials for remote shares on a Faspex server or
the client ID/secret, private key file and organization for Aspera Files.

The file is required to be present in order to use the "(remote) source" option
(-s) on the "aspera faspex browse/send" command or "aspera files send".

Although these credentials are not system username/passwords, file permissions
should reflect the sensitive nature of the credentials in that file.
