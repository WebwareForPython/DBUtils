from WebKit.URLParser import URLParameterParser, FileParser
import os
urlParser = URLParameterParser(FileParser(os.path.dirname(__file__)))
