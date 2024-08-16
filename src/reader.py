#!/usr/bin/env python3

"""Get a cleaner version of a web page for reading purposes.

This script reads JSON input from the Postlight Parser 
(https://github.com/postlight/parser) and performs conversion of HTML 
to markdown and plain-text via html2text.
"""

import sys
import json
import textwrap

from datetime import datetime
from html import unescape
from html2text import HTML2Text

class Format():
    """This is a decorator class for registering document format methods.
    
    You can register additional document formatter functions by decorating
    them with @Format.
    
    A formatter should be a function that takes as input a response object
    from the postlight-parser API.  It's output can be any string derived 
    from that input.
    
    By convention formatters should have a '_format' suffix in their function
    name.  By this convention, if you have a formatter named 'json_format',
    then you can call this with Format.formatter['json']().
    """
    formatter = {}
    def __init__(self, f):
        key, _ = f.__name__.rsplit('_', 1)
        self.formatter.update({key: f})
        self.format = f
    
    def __call__(self):
        self.format()

def format_date(obj):
    date = obj.get('date_published')
    if date is not None:        
        obj['date_published'] = datetime.strptime(
            obj['date_published'],
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )

@Format
def json_format(obj):
    """Formatter that formats as JSON"""
    return json.dumps(obj, ensure_ascii=False)

@Format
def md_format(obj):
    """Formatter that formats as markdown"""
    format_date(obj)
    content = '''
    date: {date_published}  
    author(s): {author}  
    
    # [{title}]({url})
    '''
    return '\n'.join((
        textwrap.dedent(content.format(**obj)),
        obj['content'].get('markdown', '')
    ))

@Format
def txt_format(obj):
    """Formatter that formats as plain-text"""
    format_date(obj)
    content = '''
    url: {url}
    date: {date_published}
    author(s): {author}
    
    {title}
    '''
    return '\n'.join((
        textwrap.dedent(content.format(**obj)),
        obj['content'].get('text', '')
    ))

def load(filename):
    """Load parser JSON results from file as a Python dict"""
    try:
        if filename in {"-", None}:
            return json.loads(sys.stdin.read())
        with open(filename, mode='r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f'failed to load JSON from file: {filename}', file=sys.stderr)
        sys.exit(1)

def main(result, body_width):
    """Convert parse result dict to Markdown and plain-text
    
    result: dict (a postlight-parser result)
    body_width: int (line hard-wrap length)
    """
    text = HTML2Text()
    text.body_width = body_width
    text.ignore_emphasis = True
    text.ignore_images = True
    text.ignore_links = True
    text.convert_charrefs = True
    markdown = HTML2Text()
    markdown.body_width = body_width
    markdown.convert_charrefs = True
    result['content'] = {
        'html': result['content'],
        'markdown': unescape(markdown.handle(result['content'])),
        'text': unescape(text.handle(result['content']))
    }
    return result

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=__doc__
    )
    parser.add_argument(
        'filename',
        help=(
            'load postlight-parser JSON result from file (use "-" '
            'to read from stdin)'
        )
    )
    parser.add_argument(
        '-f', '--format',
        choices=list(Format.formatter),
        default='json',
        help='output format'
    )
    parser.add_argument(
        '-w', '--body-width',
        type=int,
        default=None,
        help='character offset at which to wrap lines for plain-text'
    )
    args = parser.parse_args()
    obj = main(
        load(args.filename),
        args.body_width,
    )
    print(Format.formatter[args.format](obj))
