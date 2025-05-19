from .base_processor import BaseProcessor
from .pdf_processor import PDFProcessor
from .json_processor import JSONProcessor
from .markdown_processor import MarkdownProcessor
from .excel_processor import ExcelProcessor
from .csv_processor import CSVProcessor
from .fmea_processor import FMEAProcessor
from .tara_processor import TARAProcessor

# Import signal database processor
try:
    from .signal_processor import SignalDatabaseProcessor
    has_signal_processor = True
except ImportError:
    has_signal_processor = False

# Import additional processors if they exist
try:
    from .arxml_processor import ARXMLProcessor
    if has_signal_processor:
        __all__ = ['BaseProcessor', 'PDFProcessor', 'JSONProcessor', 'MarkdownProcessor', 
                  'ExcelProcessor', 'CSVProcessor', 'FMEAProcessor', 'TARAProcessor',
                  'ARXMLProcessor', 'SignalDatabaseProcessor']
    else:
        __all__ = ['BaseProcessor', 'PDFProcessor', 'JSONProcessor', 'MarkdownProcessor', 
                  'ExcelProcessor', 'CSVProcessor', 'FMEAProcessor', 'TARAProcessor',
                  'ARXMLProcessor']
except ImportError:
    if has_signal_processor:
        __all__ = ['BaseProcessor', 'PDFProcessor', 'JSONProcessor', 'MarkdownProcessor', 
                  'ExcelProcessor', 'CSVProcessor', 'FMEAProcessor', 'TARAProcessor',
                  'SignalDatabaseProcessor']
    else:
        __all__ = ['BaseProcessor', 'PDFProcessor', 'JSONProcessor', 'MarkdownProcessor', 
                  'ExcelProcessor', 'CSVProcessor', 'FMEAProcessor', 'TARAProcessor']

try:
    from .odx_processor import ODXProcessor
    __all__.append('ODXProcessor')
except ImportError:
    pass
