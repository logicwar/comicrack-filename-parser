# -*- coding: utf-8 -*-
import re
import clr
import System

# WinForms
clr.AddReference("System")
clr.AddReference("System.Xml")
clr.AddReference("System.Drawing")
clr.AddReference("System.Windows.Forms")

from System.IO import Path
from System.Xml import XmlDocument, XmlWriter, XmlWriterSettings

from System.Drawing import Size, Point
from System.Windows.Forms import (
    Form, Label, TextBox, Button, CheckBox, GroupBox,
    DialogResult, MessageBox, ScrollBars
)

# --------------------------------------------------------------------------------------
# Paths / defaults
# --------------------------------------------------------------------------------------
PLUGIN_DIR = Path.GetDirectoryName(__file__)
CONFIG_PATH = Path.Combine(PLUGIN_DIR, 'config.xml')

DEFAULT_CONFIG = {
    "patterns": [
        r"^(?P<number>\d{1,6})\s*-\s*(?P<title>.+)?$",
        r"^(?P<number>\d{1,6})\s*-\s*(?P<series>[^-]+?)(?:\s*-\s*(?P<title>.+))?$",
        r"^(?P<number>\d{1,6})\s*-\s*(?P<series>.+?)\s*\((?P<year>\d{4})\)$",
        r"^(?P<series>.+?)\s+\((?P<volume>\d{4})\)\s*#(?P<number>[\dA-Za-z\.]+)(?:\s*-\s*(?P<title>.*))?$",
    ],
    "overwrite": False,
    "strip_extension": True,
    "normalize_underscores": True,
    "strip_leading_zeros": False
}

SUPPORTED_GROUPS = set(['series','volume','number','year','title','month','day'])


# --------------------------------------------------------------------------------------
# Config I/O (XML)
# --------------------------------------------------------------------------------------
def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        doc = XmlDocument()
        doc.Load(CONFIG_PATH)
        root = doc.DocumentElement
        if root is None: 
            return cfg

        # booleans (with safe defaults)
        def _attr_bool(name, default):
            try:
                val = root.GetAttribute(name)
                if val is None or val == "":
                    return default
                return val.lower() == "true"
            except:
                return default

        cfg["overwrite"]            = _attr_bool("overwrite",            DEFAULT_CONFIG["overwrite"])
        cfg["strip_extension"]      = _attr_bool("strip_extension",      DEFAULT_CONFIG["strip_extension"])
        cfg["normalize_underscores"]= _attr_bool("normalize_underscores",DEFAULT_CONFIG["normalize_underscores"])
        cfg["strip_leading_zeros"]  = _attr_bool("strip_leading_zeros",  DEFAULT_CONFIG["strip_leading_zeros"])

        # patterns
        cfg["patterns"] = []
        patterns_nodes = root.GetElementsByTagName("Patterns")
        if patterns_nodes.Count > 0:
            for pat_node in patterns_nodes[0].GetElementsByTagName("Pattern"):
                if pat_node.InnerText:
                    cfg["patterns"].append(pat_node.InnerText)
        else:
            # tolerate legacy files with flat Pattern elements under root
            for pat_node in root.GetElementsByTagName("Pattern"):
                if pat_node.InnerText:
                    cfg["patterns"].append(pat_node.InnerText)

        if not cfg["patterns"]:
            cfg["patterns"] = list(DEFAULT_CONFIG["patterns"])
    except:
        # if anything fails, fall back to defaults
        pass
    return cfg

def save_config(cfg):
    try:
        settings = XmlWriterSettings()
        settings.Indent = True
        writer = XmlWriter.Create(CONFIG_PATH, settings)

        writer.WriteStartDocument()
        writer.WriteStartElement("Config")

        def _w(name, val, default):
            v = default if val is None else bool(val)
            writer.WriteAttributeString(name, str(v).lower())

        _w("overwrite",            cfg.get("overwrite"),             DEFAULT_CONFIG["overwrite"])
        _w("strip_extension",      cfg.get("strip_extension"),       DEFAULT_CONFIG["strip_extension"])
        _w("normalize_underscores",cfg.get("normalize_underscores"), DEFAULT_CONFIG["normalize_underscores"])
        _w("strip_leading_zeros",  cfg.get("strip_leading_zeros"),   DEFAULT_CONFIG["strip_leading_zeros"])

        writer.WriteStartElement("Patterns")
        for pat in cfg.get("patterns", []) or []:
            writer.WriteElementString("Pattern", pat)
        writer.WriteEndElement()  # Patterns

        writer.WriteEndElement()  # Config
        writer.WriteEndDocument()
        writer.Close()
        return True
    except Exception as ex:
        try:
            MessageBox.Show("Filename Parser: Failed to save config: %s" % ex)
        except:
            pass
        return False

# --------------------------------------------------------------------------------------
# Core parsing
# --------------------------------------------------------------------------------------
def _prepare_name(raw, cfg):
    name = raw or ""
    if cfg.get('strip_extension', True):
        name = Path.GetFileNameWithoutExtension(name)
    if cfg.get('normalize_underscores', True):
        name = name.replace('_', ' ')
    return name.strip()

def _match(name, cfg):
    text = _prepare_name(name, cfg)
    for pat in cfg.get('patterns', []):
        try:
            m = re.match(pat, text, re.IGNORECASE | re.UNICODE)
        except Exception:
            continue
        if m:
            data = {}
            for k, v in m.groupdict().items():
                if v is None: 
                    continue
                v = v.strip()
                if k == 'number' and cfg.get('strip_leading_zeros', False):
                    try:
                        v = re.sub(r'^0+(?=\d)', '', v)
                    except:
                        pass
                data[k] = v
            return data
    return None

def _set_if(book, attr, value, overwrite):
    try:
        cur = getattr(book, attr)
    except:
        cur = None
    try:
        is_empty = (cur is None) or (isinstance(cur, basestring) and cur.strip() == '')
    except:
        try:
            is_empty = (cur is None) or (isinstance(cur, str) and cur.strip() == '')
        except:
            is_empty = True
    if not (overwrite or is_empty):
        return
    try:
        if attr in ('Year','Month','Day','Volume'):
            try:
                value = int(value)
            except:
                pass
        setattr(book, attr, value)
    except:
        pass

def _apply(book, groups, cfg):
    ow = cfg.get('overwrite', False)
    if 'series' in groups: _set_if(book, 'Series', groups['series'], ow)
    if 'volume' in groups: _set_if(book, 'Volume', groups['volume'], ow)
    if 'number' in groups: _set_if(book, 'Number', groups['number'], ow)
    if 'title'  in groups: _set_if(book, 'Title',  groups['title'],  ow)
    if 'year'   in groups: _set_if(book, 'Year',   groups['year'],   ow)
    if 'month'  in groups: _set_if(book, 'Month',  groups['month'],  ow)
    if 'day'    in groups: _set_if(book, 'Day',    groups['day'],    ow)
    for k, v in groups.items():
        if k.startswith('custom_'):
            try:
                book.SetCustomValue(k[len('custom_'):], v)
            except:
                pass

# --------------------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------------------
class ConfigForm(Form):
    def __init__(self, cfg):
        Form.__init__(self)
        self.Text = 'Filename Parser — Configuration'
        self.ClientSize = Size(780, 570)

        self.lbl = Label(Text='Regex patterns (one per line). Use named groups: series, volume, number, year, title, month, day, custom_*')
        self.lbl.Location = Point(12, 12); self.lbl.AutoSize = True

        self.txt = TextBox(); self.txt.Multiline = True; self.txt.ScrollBars = ScrollBars.Vertical
        self.txt.Location = Point(12, 35); self.txt.Size = Size(756, 300)

        self.chkOverwrite  = CheckBox(Text='Overwrite non-empty fields');           self.chkOverwrite.Location  = Point(12, 345); self.chkOverwrite.AutoSize = True
        self.chkUnderscore = CheckBox(Text='Normalize underscores to spaces');      self.chkUnderscore.Location = Point(12, 370); self.chkUnderscore.AutoSize = True
        self.chkExt        = CheckBox(Text='Strip file extension before matching'); self.chkExt.Location        = Point(12, 395); self.chkExt.AutoSize = True
        self.chkZero       = CheckBox(Text='Strip leading zeros in Number (001 → 1)'); self.chkZero.Location   = Point(12, 420); self.chkZero.AutoSize = True

        self.grp = GroupBox(Text='Test regex'); self.grp.Location = Point(12, 450); self.grp.Size = Size(756, 86)
        self.txtTest = TextBox(); self.txtTest.Location = Point(12, 25); self.txtTest.Size = Size(600, 20)
        self.btnTest = Button(Text='Test'); self.btnTest.Location = Point(620, 23); self.btnTest.Click += self.on_test
        self.lblResult = Label(Text='—'); self.lblResult.Location = Point(12, 55); self.lblResult.AutoSize = True
        self.grp.Controls.Add(self.txtTest); self.grp.Controls.Add(self.btnTest); self.grp.Controls.Add(self.lblResult)

        self.btnSave = Button(Text='Save');   self.btnSave.Location   = Point(588, 540); self.btnSave.Click   += self.on_save
        self.btnCancel = Button(Text='Cancel'); self.btnCancel.Location = Point(684, 540); self.btnCancel.Click += self.on_cancel

        # Load into UI
        self.txt.Text = "\r\n".join(cfg.get('patterns', []))
        self.chkOverwrite.Checked  = bool(cfg.get('overwrite', False))
        self.chkUnderscore.Checked = bool(cfg.get('normalize_underscores', True))
        self.chkExt.Checked        = bool(cfg.get('strip_extension', True))
        self.chkZero.Checked       = bool(cfg.get('strip_leading_zeros', False))

        for c in (self.lbl, self.txt, self.chkOverwrite, self.chkUnderscore, self.chkExt, self.chkZero, self.grp, self.btnSave, self.btnCancel):
            self.Controls.Add(c)

        self.cfg = cfg
        #self.AcceptButton = self.btnSave
        self.CancelButton = self.btnCancel

    # ---- Rewritten for XML backend ----
    def on_save(self, *_):
        cfg = {
            'patterns': [p.strip() for p in self.txt.Text.splitlines() if p.strip()],
            'overwrite': self.chkOverwrite.Checked,
            'normalize_underscores': self.chkUnderscore.Checked,
            'strip_extension': self.chkExt.Checked,
            'strip_leading_zeros': self.chkZero.Checked,
        }
        if save_config(cfg):
            self.DialogResult = DialogResult.OK
            self.Close()
        else:
            MessageBox.Show("Filename Parser: Could not save config.xml. Check write permissions.")

    def on_cancel(self, *_):
        self.DialogResult = DialogResult.Cancel
        self.Close()

    def on_test(self, *_):
        # Use current UI values (without saving) to test match
        temp_cfg = {
            'patterns': [p.strip() for p in self.txt.Text.splitlines() if p.strip()],
            'overwrite': self.chkOverwrite.Checked,
            'normalize_underscores': self.chkUnderscore.Checked,
            'strip_extension': self.chkExt.Checked,
            'strip_leading_zeros': self.chkZero.Checked,
        }
        sample = self.txtTest.Text or ''
        data = _match(sample, temp_cfg)
        if not data:
            self.lblResult.Text = 'No match.'
        else:
            self.lblResult.Text = ', '.join(["%s=%s" % (k, v) for k, v in sorted(data.items())])

# --------------------------------------------------------------------------------------
# Menu entries (CE style)
# --------------------------------------------------------------------------------------

# Entry 1: Parse selected books
#@Name Parse from Filename
#@Hook Books
#@Key FilenameParser-main
#@Description Fill Series/Number/Title/Year/Volume from filename using configurable regex patterns
#@Image FilenameParser.png
def FilenameParser_Parse(books):
    if books:
        cfg = load_config()
        updated = 0
        for book in books or []:
            try:
                fname = getattr(book, 'FileName', None) or Path.GetFileName(getattr(book, 'FilePath', ''))
                if not fname:
                    continue
                data = _match(fname, cfg)
                if data:
                    _apply(book, data, cfg)
                    updated += 1
            except Exception as ex:
                try:
                    MessageBox.Show("Filename Parser: Parse error: %s" % ex)
                except:
                    pass
        MessageBox.Show('Filename Parser: updated %d book(s).' % updated)
    else:
        MessageBox.Show('Filename Parser: No comics selected')

# Entry 2: Parse selected books
#@Name Filename Parser Configure
#@Key FilenameParser-main
#@Hook ConfigScript
#@Image FilenameParser.png
def FilenameParser_Config():
    try:
        cfg = load_config()
        form = ConfigForm(cfg)
        form.ShowDialog()
    except Exception as ex:
        MessageBox.Show("Filename Parser: Config error:\n%s" % ex)