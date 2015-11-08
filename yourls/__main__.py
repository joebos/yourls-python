"""yourls

Usage:
  yourls shorten <url> [--keyword <keyword> --title <title>]
  yourls expand <shorturl>
  yourls url-stats <shorturl>
  yourls stats <filter> <limit> [--start <start>]
  yourls db-stats

Options:
  -k <keyword>, --keyword <keyword>
  -t <title>, --title <title>
  -s <start>, --start <start>  Filter start number
"""
import os.path
from contextlib import contextmanager

import click
import requests
from configparser import ConfigParser
from yourls import YOURLSClient, YOURLSURLExistsError, YOURLSAPIError

config = ConfigParser()
config_paths = ['.yourls', os.path.expanduser('~/.yourls')]
config.read(config_paths)


def config_value(name):
    """Return callable that returns config value if it exists."""
    return lambda: config.get('yourls', name, fallback=None)


@contextmanager
def catch_exceptions():
    try:
        yield
    except (YOURLSAPIError, requests.RequestException) as exc:
        error_msg = exc.args[0]
        # Prevent duplicate "Error: ", because Click adds it too.
        error_msg = error_msg.replace('Error: ', '')
        raise click.ClickException(error_msg)


@click.group()
@click.option('--apiurl', default=config_value('apiurl'))
@click.option('--signature', default=config_value('signature'))
@click.option('--username', default=config_value('username'))
@click.option('--password', default=config_value('password'))
@click.pass_context
def cli(ctx, apiurl, signature, username, password):
    """Command line interface for YOURLS.

    Configuration parameters can be passed as switches or stored in .yourls or
    ~/.yourls.

    \b
    Please provide one of the following:
    • apiurl and signature
    • apiurl, username, and password

    Configuration file format:

    \b
    [yourls]
    apiurl = http://example.com/yourls-api.php
    signature = abcdefghij
    """
    if apiurl is None:
        raise click.UsageError("apiurl missing. See 'yourls --help'")
    if signature is None and (username is None or password is None):
        raise click.UsageError("authentication paremeter(s) missing. "
                               "See 'yourls --help'")
    if signature is not None and (username is not None or password is not None):
        raise click.UsageError("authentication paremeters overspecified. "
                               "See 'yourls --help'")
    if signature:
        ctx.obj = YOURLSClient(apiurl=apiurl, signature=signature)
    else:
        ctx.obj = YOURLSClient(apiurl=apiurl, username=username, password=password)


@cli.command()
@click.argument('url')
@click.option('--keyword', '-k')
@click.option('--title', '-t')
@click.option('--only-new/--allow-existing', default=False,
              help="Exit with error if URL has already been shortened. "
                   "(Default: allow existing)")
@click.option('--simple', '-s', is_flag=True,
              help='Print short URL instead of full ShortenedURL object')
@click.pass_obj
def shorten(yourls, url, keyword, title, only_new, simple):
    new = True
    try:
        shorturl = yourls.shorten(url, keyword=keyword, title=title)
    except YOURLSURLExistsError as exc:
        shorturl = exc.url
        new = False
        if only_new:
            raise click.ClickException(exc.args[0])
    except (YOURLSAPIError, requests.RequestException) as exc:
        raise click.ClickException(exc.args[0])

    if simple:
        shorturl = shorturl.shorturl

    if only_new:
        status = ''
    else:
        status = 'New: ' if new else 'Exists: '

    click.echo('{status}{shorturl}'.format(status=status, shorturl=shorturl))


@cli.command()
@click.argument('shorturl')
@click.pass_obj
def expand(yourls, shorturl):
    with catch_exceptions():
        longurl = yourls.expand(shorturl)
    click.echo(longurl)


@cli.command('url-stats')
@click.argument('shorturl')
@click.option('--simple', '-s', is_flag=True,
              help='Print short URL instead of full ShortenedURL object')
@click.pass_obj
def url_stats(yourls, shorturl, simple):
    with catch_exceptions():
        shorturl = yourls.url_stats(shorturl)

    if simple:
        shorturl = shorturl.shorturl

    click.echo(shorturl)


@cli.command()
@click.argument('filter', type=click.Choice(('top', 'bottom', 'rand', 'last')))
@click.argument('limit', type=int)
@click.option('--start', '-s', type=int)
@click.option('--simple', '-s', is_flag=True,
              help='Print short URLs instead of full ShortenedURL objects')
@click.pass_obj
def stats(yourls, filter, limit, start, simple):
    with catch_exceptions():
        links, stats = yourls.stats(filter=filter, limit=limit, start=start)
    click.echo(stats)
    for link in links:
        if simple:
            link = link.shorturl
        click.echo(link)


@cli.command('db-stats')
@click.pass_obj
def db_stats(yourls):
    with catch_exceptions():
        stats = yourls.db_stats()
    click.echo(stats)

if __name__ == '__main__':
    cli(prog_name='yourls')