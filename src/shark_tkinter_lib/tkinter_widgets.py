# Copyright (c) 2018 SMHI, Swedish Meteorological and Hydrological Institute
# License: MIT License (see LICENSE.txt or http://opensource.org/licenses/mit).

import calendar
import datetime
import logging
import re
import tkinter as tk
from tkinter import font
from tkinter import ttk

import numpy as np

try:
    import pandas as pd
except:
    pass

# try:
#     from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
#     import matplotlib.dates as dates
# except:
#     pass

logger = logging.getLogger(__name__)


class CalendarWidget(tk.Frame):
    """
    TEST RUN:

    def test():
        root = tk.Tk()
        root.title('Date selection')
        ttkcal = CalendarWidget(firstweekday=calendar.SUNDAY, root=root)
        ttkcal.pack(expand=1, fill='both')

        root.mainloop()
        print(ttkcal.selection)

    if __name__ == '__main__':
        test()

    """

    datetime = calendar.datetime.datetime
    timedelta = calendar.datetime.timedelta

    def __init__(self, master=None, **kw):
        """
        WIDGET-SPECIFIC OPTIONS

            locale, firstweekday, year, month, selectbackground,
            selectforeground
        """
        # remove custom options from kw before initializating ttk.Frame
        fwday = kw.pop('firstweekday', calendar.MONDAY)
        year = kw.pop('year', self.datetime.now().year)
        month = kw.pop('month', self.datetime.now().month)
        locale = kw.pop('locale', None)
        sel_bg = kw.pop('selectbackground', '#ecffc4')
        sel_fg = kw.pop('selectforeground', '#05640e')

        self._date = self.datetime(year, month, 1)
        self._selection = None  # no date selected
        self.selected_date = None
        self.master = tk.Tk()
        self.master.title('Date selection')

        tk.Frame.__init__(self, self.master, **kw)

        self._cal = get_calendar(locale, fwday)

        self.__setup_styles()       # creates custom styles
        self.__place_widgets()      # pack/grid used widgets
        self.__config_calendar()    # adjust calendar columns and setup tags
        # configure a canvas, and proper bindings, for selecting dates
        self.__setup_selection(sel_bg, sel_fg)

        # store items ids, used for insertion later
        self._items = [self._calendar.insert('', 'end', values='') for _ in range(6)]
        # insert dates in the currently empty calendar
        self._build_calendar()

        # set the minimal size for the widget
        self._calendar.bind('<Map>', self.__minsize)

    def __setitem__(self, item, value):
        if item in ('year', 'month'):
            raise AttributeError("attribute '%s' is not writeable" % item)
        elif item == 'selectbackground':
            self._canvas['background'] = value
        elif item == 'selectforeground':
            self._canvas.itemconfigure(self._canvas.text, item=value)
        else:
            ttk.Frame.__setitem__(self, item, value)

    def __getitem__(self, item):
        if item in ('year', 'month'):
            return getattr(self._date, item)
        elif item == 'selectbackground':
            return self._canvas['background']
        elif item == 'selectforeground':
            return self._canvas.itemcget(self._canvas.text, 'fill')
        else:
            r = ttk.tclobjs_to_py({item: ttk.Frame.__getitem__(self, item)})
            return r[item]

    def __setup_styles(self):
        # custom ttk styles
        style = ttk.Style(self.master)

        def arrow_layout(direction):
            return [('Button.focus', {'children': [('Button.%sarrow' % direction, None)]})]

        style.layout('L.TButton', arrow_layout('left'))
        style.layout('R.TButton', arrow_layout('right'))

    def dummy(self):
        pass

    def __place_widgets(self):
        # header frame and its widgets
        hframe = ttk.Frame(self)
        lbtn = ttk.Button(hframe, style='L.TButton', command=self._prev_month)
        rbtn = ttk.Button(hframe, style='R.TButton', command=self._next_month)

        self.okbtn = ttk.Button(hframe, text='Ok', command=self.destroy_calendar)
        self._header = ttk.Label(hframe, width=15, anchor='center')
        # the calendar
        self._calendar = ttk.Treeview(self.master, show='', selectmode='none', height=7)

        # pack the widgets
        hframe.pack(in_=self, side='top', pady=4, anchor='center')
        lbtn.grid(in_=hframe)
        self._header.grid(in_=hframe, column=1, row=0, padx=12)
        rbtn.grid(in_=hframe, column=2, row=0)
        self._calendar.pack(in_=self, expand=1, fill='both', side='bottom')
        self.okbtn.grid(in_=hframe, column=1, row=2)

    def __config_calendar(self):
        cols = self._cal.formatweekheader(3).split()
        self._calendar['columns'] = cols
        self._calendar.tag_configure('header', background='grey90')
        self._calendar.insert('', 'end', values=cols, tag='header')
        # adjust its columns width
        tkfont = font.Font()
        maxwidth = max(tkfont.measure(col) for col in cols)
        for col in cols:
            self._calendar.column(col, width=maxwidth*1, minwidth=maxwidth, anchor='e')

    def __setup_selection(self, sel_bg, sel_fg):
        self._font = font.Font()
        self._canvas = canvas = tk.Canvas(self._calendar, background=sel_bg, borderwidth=0, highlightthickness=0)
        canvas.text = canvas.create_text(0, 0, fill=sel_fg, anchor='w')

        canvas.bind('<ButtonPress-1>', lambda evt: canvas.place_forget())
        self._calendar.bind('<Configure>', lambda evt: canvas.place_forget())
        self._calendar.bind('<ButtonPress-1>', self._pressed)

    def __minsize(self, *args):
        pass
        #FIXME AttributeError: 'CalendarWidget' object has no attribute 'minsize'
        # width, height = self._calendar.master.geometry().split('x')
        # height = height[:height.index('+')]
        # width, height = '300', '200'
        # self._calendar.master.minsize(width, height)

    def _build_calendar(self):
        year, month = self._date.year, self._date.month

        # update header text (Month, YEAR)
        header = self._cal.formatmonthname(year, month, 0)
        self._header['text'] = header.title()

        # update calendar shown dates
        cal = self._cal.monthdayscalendar(year, month)
        for idx, item in enumerate(self._items):
            week = cal[idx] if idx < len(cal) else []
            fmt_week = [('%02d' % day) if day else '' for day in week]
            self._calendar.item(item, values=fmt_week)

    def _show_selection(self, text, bbox):
        """Configure canvas for a new selection."""
        x, y, width, height = bbox

        textwidth = self._font.measure(text)

        canvas = self._canvas
        canvas.configure(width=width, height=height)
        canvas.coords(canvas.text, width - textwidth, height / 2 - 1)
        canvas.itemconfigure(canvas.text, text=text)
        canvas.place(in_=self._calendar, x=x, y=y)

    def _pressed(self, evt):
        """Clicked somewhere in the calendar."""
        x, y, widget = evt.x, evt.y, evt.widget
        item = widget.identify_row(y)
        column = widget.identify_column(x)

        if not column or item not in self._items:
            # clicked in the weekdays row or just outside the columns
            return

        item_values = widget.item(item)['values']
        if not len(item_values):  # row is empty for this month
            return

        text = item_values[int(column[1]) - 1]
        if not text:  # date is empty
            return

        bbox = widget.bbox(item, column)
        if not bbox:  # calendar not visible yet
            return

        # update and then show selection
        text = '%02d' % text
        self._selection = (text, item, column)
        self._show_selection(text, bbox)

    def _prev_month(self):
        """Updated calendar to show the previous month."""
        self._canvas.place_forget()

        self._date = self._date - self.timedelta(days=1)
        self._date = self.datetime(self._date.year, self._date.month, 1)
        self._build_calendar()  # reconstuct calendar

    def _next_month(self):
        """Update calendar to show the next month."""
        self._canvas.place_forget()

        year, month = self._date.year, self._date.month
        self._date = self._date + self.timedelta(
            days=calendar.monthrange(year, month)[1] + 1)
        self._date = self.datetime(self._date.year, self._date.month, 1)
        self._build_calendar()  # reconstruct calendar

    def destroy_calendar(self):
        """
        :return:
        """
        self.destroy()
        self.master.destroy()
        # print('Destroyed!')

    @property
    def selection(self):
        """Return a datetime representing the current selected date."""
        if not self._selection:
            return None

        year, month = self._date.year, self._date.month
        return self.datetime(year, month, int(self._selection[0]))


class CheckbuttonWidgetSingle(tk.Frame):
    def __init__(self,
                 parent,
                 name='Checkbutton',
                 callback=None,
                 prop_cbutton={},
                 grid_cbutton={},
                 prop_frame={},
                 **kwargs):

        self.name = name
        self.callback = callback
        # Save inputs
        self.prop_frame = {}
        self.prop_frame.update(prop_frame)

        self.grid_frame = {'row': 0,
                           'column': 0,
                           'sticky': 'w',
                           'rowspan': 1,
                           'columnspan': 1}
        self.grid_frame.update(kwargs)

        self.prop_cbutton = {}
        self.prop_cbutton.update(prop_cbutton)

        self.grid_cbutton = {'sticky': 'w',
                              'padx': 2,
                              'pady': 0}
        self.grid_cbutton.update(grid_cbutton)

        # Create frame
        tk.Frame.__init__(self, parent, **self.prop_frame)
        self.grid(**self.grid_frame)

        self._set_frame()

    def _set_frame(self):
        self.booleanvar = tk.BooleanVar()
        self.checkbutton = tk.Checkbutton(self,
                                          text=self.name,
                                          variable=self.booleanvar,
                                          comman=self._on_toggle,
                                          **self.prop_cbutton)
        self.checkbutton.grid(**self.grid_cbutton)
        grid_configure(self)

    def _on_toggle(self):
        if self.callback:
            self.callback()

    def get(self):
        return self.booleanvar.get()

    def set(self, value):
        self.booleanvar.set(value)

    def get_value(self):
        return self.booleanvar.get()

    def set_value(self, value):
        self.booleanvar.set(value)


class CheckbuttonWidget(tk.Frame):
    """
    Frame to hold tk.Checkbuttons. 
    Names of checkbuttons are listed in "items". 
    Option to:
        include a "Select all" checkbutton at the bottom
        allow similar parameters to be selected (ex. SALT_BTL and SALT_CTD can not be checked att the same time if 
            allow_similar_parameters_to_be_checked=False
    """
     
    def __init__(self, 
                 parent, 
                 items=[], 
                 pre_checked_items=[],
                 nr_rows_per_column=10, 
                 include_select_all=True, 
                 allow_similar_parameters_to_be_checked=True, 
                 colors={}, 
                 sort_items=False, 
                 prop_cbuttons={}, 
                 grid_cbuttons={},
                 prop_frame={}, 
                 font=(), 
                 **kwargs):
        
        # Save inputs
        self.prop_frame = {}
        self.prop_frame.update(prop_frame)
        
        self.grid_frame = {'row': 0, 
                           'column': 0, 
                           'sticky': 'w', 
                           'rowspan': 1, 
                           'columnspan': 1}
        self.grid_frame.update(kwargs)
        
        self.prop_cbuttons = {}
        self.prop_cbuttons.update(prop_cbuttons)
        
        self.grid_cbuttons = {'sticky':'w', 
                              'padx':2,
                              'pady':0}
        self.grid_cbuttons.update(grid_cbuttons)
        
        self.pre_checked_items = pre_checked_items[:]
        self.nr_rows_per_column = nr_rows_per_column
        self.include_select_all = include_select_all
        self.allow_similar_parameters_to_be_checked = allow_similar_parameters_to_be_checked
        self.colors = colors
        
        if sort_items:
            self.items = sorted(items) 
        else:
            self.items = items[:]
        
        self.cbutton = {}
        self.booleanvar = {}
        self.disabled_list = []
        
        # Create frame
        tk.Frame.__init__(self, parent, **self.prop_frame)
        self.grid(**self.grid_frame)
        
        self._set_frame()
        
    #===========================================================================
    def _set_frame(self):
        r=0
        c=0

        for item in self.items:
            self.booleanvar[item] = tk.BooleanVar()
            self.booleanvar[item].set(True)
            self.cbutton[item] = tk.Checkbutton(self, 
                                              text=item,  
                                              variable=self.booleanvar[item], 
                                              command=lambda item=item: self._on_select_item(item), 
                                              **self.prop_cbuttons)
            self.cbutton[item].grid(row=r, column=c, **self.grid_cbuttons)
            if item in self.pre_checked_items:
                self.booleanvar[item].set(True)
            if item in self.colors:
                self.cbutton[item].config(fg=self.colors[item])
            r+=1
            if not r%self.nr_rows_per_column:
                c+=1
                r=0

        
        if self.include_select_all:
            prop = dict((k, v) for k, v in self.prop_cbuttons.items() if k in ['padx', 'pady'])
            ttk.Separator(self, orient=u'horizontal').grid(row=r, column=c, sticky=u'ew', **prop)
            r+=1
            self.booleavar_select_all = tk.BooleanVar()
            self.cbutton_select_all = tk.Checkbutton(self, 
                                                      text=u'Select all',  
                                                      variable=self.booleavar_select_all, 
                                                      command=self._on_select_all,
                                                      **self.prop_cbuttons)
            self.cbutton_select_all.grid(row=r, column=c, **self.grid_cbuttons)
            
            if self.items == self.pre_checked_items:
                self.booleavar_select_all.set(True)
    
    #===========================================================================
    def _on_select_item(self, source_item):
        
        if not self.allow_similar_parameters_to_be_checked:
            if self.booleanvar[source_item].get():
                for item in self.items:
                    if self.booleanvar[item].get() and item != source_item and item.startswith(source_item[:4]):
                        self.cbutton[item].deselect()
        
        if self.include_select_all:  
            if all([self.booleanvar[item].get() for item in self.items]):
                self.cbutton_select_all.select()
            else:
                self.cbutton_select_all.deselect()
            
            
    #===========================================================================
    def _on_select_all(self):
        if self.booleavar_select_all.get():
            for item in self.items:
                if item not in self.disabled_list:
                    self.cbutton[item].select()
        else:
            for item in self.items:
                self.cbutton[item].deselect()
          
    #===========================================================================
    def _add_to_disabled(self, item):
        if item not in self.disabled_list:
            self.disabled_list.append(item)
        self._check_disable_list()
        
    #===========================================================================
    def _remove_from_disabled(self, item):
        if item in self.disabled_list:
            self.disabled_list.pop(self.disabled_list.index(item))
            self._check_disable_list()
    
    #===========================================================================
    def _check_disable_list(self):
        # print('%%'*50)
        # print(sorted(self.disabled_list))
        # print(sorted(self.items))
        try:
            if not self.disabled_list:
                self.cbutton_select_all.config(state=u'normal')
            elif sorted(self.disabled_list) == sorted(self.items):
                self.cbutton_select_all.config(state=u'disabled')
            else:
                self.cbutton_select_all.config(state=u'normal')
        except:
            pass
            
    #===========================================================================
    def reset_selection(self):
        for item in self.items:
            self.cbutton[item].deselect()
            self.activate(item)
        try:
            self.cbutton_select_all.deselect()
        except:
            pass

    def select(self, item):
        if item in self.cbutton:
            self.cbutton[item].select()
        
    #===========================================================================
    def deactivate(self, item):
        self.cbutton[item].deselect()
        self.cbutton[item].config(state=u'disabled')
        self._add_to_disabled(item)

    def deactivate_all(self):
        for item in self.cbutton:
            self.deactivate(item)
    
    #===========================================================================
    def activate(self, item):
        self.cbutton[item].config(state=u'normal')
        self._remove_from_disabled(item)

    def activate_all(self):
        for item in self.cbutton:
            self.activate(item)

    def set_value(self, values):
        """
        Sets values. First diactivate and thena activate values if string or list.
        :param values:
        :return:
        """
        self.reset_selection()
        if type(values) == str:
            values = [values]

        for item in values:
            if item in self.cbutton:
                self.select(item)

    def get_value(self):
        """
        Returns all checkt items as a list.
        :return:
        """
        return self.get_checked_item_list()

    #===========================================================================
    def get_checked_item_list(self):
        return_list = []
        for item in self.items:
            if self.booleanvar[item].get():
                return_list.append(item)
                
        return return_list
    
    #===========================================================================
    def change_color(self, item, new_color):
        self.cbutton[item].config(fg=new_color)
        self.cbutton[item].update_idletasks()
        self.cbutton[item].update()
        self.update()
        self.update_idletasks()
        
        
"""
================================================================================
================================================================================
================================================================================
"""
class ComboboxWidget(tk.Frame):
    """
    Updated 20180825    
    """
    def __init__(self, 
                 parent=False, 
                 title='',
                 align='vertical',
                 items=[], 
                 default_item=None, 
                 prop_frame={}, 
                 prop_combobox={}, 
                 grid_items={}, 
                 callback_target=[], 
                 **kwargs):
        
        self.parent = parent
        self.title = title
        self.align = align
        
        self.selected_item = None
        
        if not isinstance(callback_target, list):
            self.callback_targets = [callback_target]
        else:
            self.callback_targets = callback_target
        
        self.prop_frame = {}
        self.prop_frame.update(prop_frame)
        
        self.prop_combobox = {'width':20, 
                              'state':'readonly'}
        self.prop_combobox.update(prop_combobox)
        
        self.grid_frame = {}
        self.grid_frame.update(kwargs)
        
        self.grid_items = {'padx': 5, 
                           'pady': 5, 
                           'sticky': 'w'}
        self.grid_items.update(grid_items)
        
        # Create frame
        tk.Frame.__init__(self, parent, **self.prop_frame)
        self.grid(**self.grid_frame)
        
        self._set_frame()
        
        self.update_items(items, default_item)
        

    #===========================================================================
    def _set_frame(self):
        """
        Updated 20180825    
        """
        r = 0
        c = 0
        if self.title:
            tk.Label(self, text=self.title).grid(row=r, column=c, **self.grid_items)
            if self.align == 'vertical':
                r += 1
            else:
                c += 1
        self.stringvar = tk.StringVar()
        self.combobox = ttk.Combobox(self,
                                     textvariable=self.stringvar, 
                                     **self.prop_combobox)
        self.combobox.grid(row=r, column=c, **self.grid_items)
        
        grid_configure(self, nr_rows=r+1, nr_columns=c+1)
        
        self.combobox.bind('<<ComboboxSelected>>', self._on_select)
                
    #===========================================================================
    def _on_select(self, event): 
#         print('tkw.Combobox()._on_select'
        self.selected_item = self.stringvar.get()
        
        for target in self.callback_targets:
            target()
        
    #===========================================================================
    def add_target(self, target):
        self.callback_targets.append(target)
        
    @property
    def values(self):
        return self.combobox['values']
        
    #===========================================================================
    def get_value(self): 
        """
        Created     20180821     
        """
        return self.stringvar.get() 

    def get(self):
        return self.stringvar.get()
    
    #===========================================================================
    def set_value(self, value): 
        """
        Created     20180821     
        """
        if value in self.items:
            self.stringvar.set(value) 

    def set(self, value):
        self.set_value(value)
        
    #===========================================================================
    def update_items(self, items=[], default_item=None, default_match=None):
        self.items = items[:]
        old_value = self.get_value()

        if not any([default_item, default_match]) and old_value in items:
            self.default_item = old_value
        elif not default_item and self.items:
            if default_match:
                for k, item in enumerate(self.items):
                    # print('default_match', item())
                    if default_match.lower() in item.lower():
                        self.default_item = self.items[k]
                        break
                else:
                    self.default_item = self.items[0]
            else:
                self.default_item = self.items[0]
        elif self.items and default_item not in self.items:
            self.default_item = self.items[0]
        elif default_item:
            self.default_item = default_item
        else:
            self.default_item = None
            
        # Update combobox
        self.combobox['values'] = self.items

        if self.default_item:
            self.stringvar.set(self.default_item)
        else:
            self.stringvar.set('')
            
        self.selected_item = self.stringvar.get()

    def delete_item(self, item):
        if item in self.items:
            self.items.pop(self.items.index(item))
        self.update_items(self.items, default_item=self.selected_item)
"""
================================================================================
================================================================================
================================================================================
"""
class DDListbox(tk.Listbox): 
    """ 
    A Tkinter listbox with drag'n'drop reordering of entries. 
    http://flylib.com/books/en/2.9.1.229/1/
    """ 
    def __init__(self, master, **kw): 
        kw['selectmode'] = tk.SINGLE 
        tk.Listbox.__init__(self, master, kw) 
        self.bind('<Button-1>', self.setCurrent) 
        self.bind('<B1-Motion>', self.shiftSelection) 
        self.curIndex = None 
    def setCurrent(self, event): 
        self.curIndex = self.nearest(event.y) 
    def shiftSelection(self, event): 
        i = self.nearest(event.y) 
        if i < self.curIndex: 
            x = self.get(i) 
            self.delete(i) 
            self.insert(i+1, x) 
            self.curIndex = i 
        elif i > self.curIndex: 
            x = self.get(i) 
            self.delete(i) 
            self.insert(i-1, x) 
            self.curIndex = i
            
    #===========================================================================
    def get_item_list(self):
        item_list = self.get(0, 'end')
        return list(item_list)
    
    
"""
================================================================================
================================================================================
================================================================================
"""
class EntryWidget(tk.Entry):
    
    def __init__(self, 
                 frame=False,
                 parent=False,
                 index=False, 
                 pack=True, 
                 row_in_grid=0, 
                 col_in_grid=0,
                 entry_type='general',
                 entry_id='', 
                 callback_on_focus_out=None, 
                 callback_on_focus_in=None, 
                 callback_on_return_new_row=None,
                 callback_on_change_value=None,
                 prop_entry={}, 
                 **kwargs):
        
        self.parent = parent
        self.frame = frame
        self.entry_id = entry_id
        self.index = index
        self.row_in_grid = row_in_grid
        self.col_in_grid = col_in_grid
        self.entry_type = entry_type
        self.callback_on_focus_out = callback_on_focus_out
        self.callback_on_focus_in = callback_on_focus_in
        self.callback_on_return_new_row = callback_on_return_new_row
        self.callback_on_change_value = callback_on_change_value
        
        self.stringvar = tk.StringVar()
        
        self.prop_entry = {'font': 'Helvetica 10'}
        self.prop_entry.update(prop_entry)
        
        self.grid_entry = {}
        self.grid_entry.update(kwargs)
        
        tk.Entry.__init__(self, 
                          frame, 
                          textvariable=self.stringvar,  
                          **self.prop_entry)

        self.grid(**self.grid_entry)
        
        self._load_default()
        self._activate_bindings()
        
#         self.config(state=u'readonly')
        
    #===========================================================================
    def _load_default(self):
        
        # Initiate linked entries. These are focused when return, left_key, right_key etc are pressed. 
        self.west_entry = None
        self.east_entry = None
        self.north_entry = None
        self.south_entry = None
        self.return_entry = None
        
        self.old_value = ''
        
        self.entry_state = 'normal'
        self.return_direction = 'vertical'
        
        
    #===========================================================================
    def _activate_bindings(self):
        # Bindings
        self.bind('<FocusIn>', self._on_focus_in)
        self.bind('<FocusOut>', self._on_focus_out)
        
        self.bind('<1>', self._on_mouse_1)
        
        self.bind('<Return>', self._on_key_return)
        
        self.bind('<Left>', self._on_key_left)
        self.bind('<Right>', self._on_key_right)
        self.bind('<Up>', self._on_key_up)
        self.bind('<Down>', self._on_key_down)
        
        
#         self.bind('<Escape>', self._abort)
#         self.bind('<Tab>', self._on_key_)
#         self.bind('<Shift-Tab>', self._on_key_)
#         self.bind('<Shift-Left>', self._on_key_)
#         self.bind('<Shift-Right>', self._on_key_)
        
        self.stringvar.trace("w", self._on_change_value)
    
    #===========================================================================
    def _on_focus_in(self, event=None):
        if self.entry_state != 'normal':
            pass 
        else:
            # First save old value
            self.old_value = self.stringvar.get()
            
            # Set state to normal if not 
            self.configure(state=u'normal')
            self.select_range(0, u'end')
        if not hasattr(self, 'nr_f'):
            self.nr_f = 1
        else:
            self.nr_f += 1
        print(f'focus_in: {self.nr_f}')
        if self.callback_on_focus_in:
            self.callback_on_focus_in(self)
        
    #===========================================================================
    def _on_focus_out(self, event=None):
        if self.callback_on_focus_out:
            self.callback_on_focus_out(self)
        
    #===========================================================================
    def _on_mouse_1(self, event=None):
        self.focus_entry()
    
    #===========================================================================
    def _on_key_left(self, event=None):
        if self.west_entry:
            self.west_entry.focus_entry()
            
    #===========================================================================
    def _on_key_right(self, event=None):
        if self.east_entry:
            self.east_entry.focus_entry()
            
    #===========================================================================
    def _on_key_up(self, event=None):
        if self.north_entry:
            self.north_entry.focus_entry()
            
    #===========================================================================
    def _on_key_down(self, event=None):
        if self.south_entry:
            self.south_entry.focus_entry()
        
    #===========================================================================
    def _on_key_return(self, event=None): 
        "When hitting return "
        if self.return_entry:
            if self.callback_on_return_new_row and self.row_in_grid != self.return_entry.row_in_grid:
                self.callback_on_return_new_row(self)
            self.return_entry.focus_entry()
        elif self.return_direction == 'vertical':
            self._on_key_down()
        elif self.return_direction == 'horizontal':
            self._on_key_right()

    #===========================================================================
    def _on_key_excape(self, event=None):
        """
        When hitting <Escape>
        """
        self.value.set(self.old_value)
        self.configure(state=u'readonly')
    
    #===========================================================================
    def _on_change_value(self, *dummy):
        string = self.stringvar.get().strip()
        
        if not string:
            pass
        elif self.entry_type == 'int':
            string = re.sub('\D', '', string)
        elif self.entry_type == 'float':
            string = string.replace(',', '.')
            split_value = [re.sub('\D', '', v) for v in string.split('.')]
            string = '.'.join(split_value)
        elif self.entry_type == 'path':
            string = string.replace('\\', '/')
        self.stringvar.set(string)
        if self.callback_on_change_value:
            self.callback_on_change_value()
    
    #===========================================================================
    def focus_entry(self):
        self.focus_set()
#         self._on_focus_in()

    def unfocus(self):
        self.frame.focus()
        
    #===========================================================================
    def select_text(self):
        self.select_range(0, 'end')
        
    #===========================================================================
    def set_entry_type(self, entry_type):
        self.entry_type = entry_type
        
    #===========================================================================
    def get_value(self):
        value = self.stringvar.get()
        if self.entry_type in [float, 'float']:
            if value:
                return float(value)
            else:
                return np.nan
        elif self.entry_type in [int, 'int']:
            if value:
                return int(value)
            else:
                return np.nan
        else:
            return value
    
    #===========================================================================
    def set_return_direction(self, direction='vertical'):
        self.return_direction = direction
    
    #===========================================================================
    def set_prop(self, **kwargs):
        self.config(**kwargs)
        
    #===========================================================================
    def set_state(self, state):
        self.config(state=state) 
        self.entry_state = state

    def disable_widget(self):
        self.set_state('disabled')

    def enable_widget(self):
        self.set_state('normal')

    def deactivate(self):
        self.set_state('disabled')

    def activate(self):
        self.set_state('normal')

    #===========================================================================
    def set_fg_color(self, color='black'):  
        self.configure(fg=color)

    #===========================================================================
    def set_value(self, value):
        self.old_value = self.stringvar.get()
        self.stringvar.set(value)
        
    #===========================================================================
    def reset_entry(self, force=False):
        if force:
            self.set_value('')
        else:
            if self.entry_state == 'normal':
                self.set_value('')
    
"""
================================================================================
================================================================================
================================================================================
"""
class EntryGridWidget(tk.Frame):

    #===========================================================================
    def __init__(self, 
                 parent, 
                 in_slides=True,
                 width=None, 
                 height=None, 
                 nr_rows=5, 
                 nr_columns=4, 
                 return_direction='horizontal', 
                 jump_to_next_row_or_column_on_return=True, 
                 callback_on_return_new_row=None,
                 callback_on_focus_out=None, 
                 callback_on_focus_in=None, 
                 disabled_rows=[],
                 disabled_columns=[], 
                 prop_frame={}, 
                 prop_entry={}, 
                 grid_entry={}, 
                 **kwargs):
        
        # Save input
        self.parent = parent
        self.in_slides = in_slides
        self.width = width
        self.height = height
        self.nr_rows = nr_rows
        self.nr_columns = nr_columns
        self.return_direction = return_direction
        self.jump_to_next_row_or_column_on_return = jump_to_next_row_or_column_on_return
        self.callback_on_return_new_row = callback_on_return_new_row
        self.callback_on_focus_out = callback_on_focus_out
        self.callback_on_focus_in = callback_on_focus_in
        
        self.disabled_rows = disabled_rows
        self.disabled_columns = disabled_columns
        
        self.prop_frame = {}
        self.prop_frame.update(prop_frame)
        
        self.grid_frame = {}
        self.grid_frame.update(kwargs)
        
        self.prop_entry = {}
        self.prop_entry.update(prop_entry)
        
        self.grid_entry = {}
        self.grid_entry.update(grid_entry)
        
        # Create frame
        tk.Frame.__init__(self, parent, **self.prop_frame)
        self.grid(**self.grid_frame)
        
        self._set_frame()
        self._set_entries()
        
        grid_configure(self)


    #===========================================================================
    def _set_frame(self):

        if self.in_slides:
            if not self.width:
                self.width = np.round(self.parent.winfo_width()*3/4)
            if not self.height:
                self.height = self.parent.winfo_height()*.9
    
    #         self.canvas_info = tk.Canvas(self)
            self.canvas_info = tk.Canvas(self, width=self.width, height=self.height)
            self.canvas_info.grid(row=0, column=0, sticky='nsew')
    
            self.frame_info_inner = tk.Frame(self.canvas_info)
            self.scrollbar_vertical = tk.Scrollbar(self, orient="vertical", command=self.canvas_info.yview)
            self.scrollbar_horizontal = tk.Scrollbar(self, orient="horizontal", command=self.canvas_info.xview)
            self.canvas_info.configure(xscrollcommand=self.scrollbar_horizontal.set)
            
            self.scrollbar_vertical.grid(row=0, column=1, sticky=u'ns')
            self.scrollbar_horizontal.grid(row=1, column=0, sticky=u'ew')
             
    #        self.canvas.create_window((4,4), window=self.frame)
            self.canvas_info.create_window((9,9), window=self.frame_info_inner, anchor="nw", 
                                      tags="self.frame") #???
     
            self.frame_info_inner.bind("<Configure>", self._on_frame_configure)
        else:
            self.frame_info_inner = self
            
        grid_configure(self.frame_info_inner)
        
    #===========================================================================
    def _on_frame_configure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas_info.configure(scrollregion=self.canvas_info.bbox("all"))
        
    #===========================================================================
    def _set_entries(self):
        frame = self.frame_info_inner
        
        # Create entries
        self.entries = {}
        for row in range(self.nr_rows):
            self.entries[row] = {}
            for col in range(self.nr_columns):
                ent = EntryWidget(frame, 
                                  row=row, 
                                  column=col, 
                                  entry_id='%s:%s' %(row, col), 
                                  prop_entry=self.prop_entry, 
                                  callback_on_focus_out=self.callback_on_focus_out, 
                                  callback_on_focus_in=self.callback_on_focus_in, 
                                  callback_on_return_new_row=self.callback_on_return_new_row, 
                                  row_in_grid=row, 
                                  col_in_grid=col, 
                                  **self.grid_entry)
                ent.set_return_direction(self.return_direction) 
                if row in self.disabled_rows:
                    ent.set_state('disabled')
                if col in self.disabled_columns:
                    ent.set_state('disabled')
                self.entries[row][col] = ent
        self.link_entries()
        
    #===========================================================================
    def link_entries(self):
        """
        Link adjustant entries. This is called after entry creation and when entries are disabled/enabled. 
        """
        for row in range(self.nr_rows):
            for col in range(self.nr_columns):
                if self.entries[row][col].entry_state != 'normal':
                    continue
                
                # Link north
                #---------------------------------------------------------------
                next_is_ok = False
                next_row = row
                next_col = col
                while not next_is_ok:
                    next_row-=1
                    if next_row < 0:
                        next_row = self.nr_rows-1
                    if self.entries[next_row][next_col].entry_state == 'normal':
                        next_is_ok = True
                self.entries[row][col].north_entry = self.entries[next_row][next_col]

                # Link south
                #---------------------------------------------------------------
                next_is_ok = False
                next_row = row
                next_col = col
                while not next_is_ok:
                    next_row+=1
                    if next_row == self.nr_rows:
                        next_row = 0
                    if self.entries[next_row][next_col].entry_state == 'normal':
                        next_is_ok = True
                self.entries[row][col].south_entry = self.entries[next_row][next_col]

                # Link west
                #---------------------------------------------------------------
                next_is_ok = False
                next_row = row
                next_col = col
                while not next_is_ok:
                    next_col-=1
                    if next_col < 0:
                        next_col = self.nr_columns-1
                    if self.entries[next_row][next_col].entry_state == 'normal':
                        next_is_ok = True
                self.entries[row][col].west_entry = self.entries[next_row][next_col]
                
                # Link east
                #---------------------------------------------------------------
                next_is_ok = False
                next_row = row
                next_col = col
                while not next_is_ok:
                    next_col+=1
                    if next_col == self.nr_columns:
                        next_col = 0
                    if self.entries[next_row][next_col].entry_state == 'normal':
                        next_is_ok = True
                self.entries[row][col].east_entry = self.entries[next_row][next_col]
                
                # Link return
                #---------------------------------------------------------------
                if self.jump_to_next_row_or_column_on_return:
                    next_is_ok = False
                    next_row = row
                    next_col = col
                    
                    if self.return_direction == 'horizontal':
                        while not next_is_ok:
                            next_col+=1
                            if next_col == self.nr_columns:
                                next_col = 0
                                next_row+=1
                                if next_row == self.nr_rows:
                                    next_row = 0
                            if self.entries[next_row][next_col].entry_state == 'normal':
                                next_is_ok = True
                        
                    elif self.return_direction == 'vertical':
                        while not next_is_ok:
                            next_row+=1
                            if next_row == self.nr_rows:
                                next_col+=1
                                next_row = 0
                                if next_col == self.nr_columns:
                                    next_col = 0
                            if self.entries[next_row][next_col].entry_state == 'normal':
                                next_is_ok = True    
                    self.entries[row][col].return_entry = self.entries[next_row][next_col]      
        
    #===========================================================================
    def get_entry(self, row, col):
        return self.entries[row][col]
        
    #===========================================================================
    def get_value(self, row, col):
        return self.entries[row][col].get_value()
    
    #===========================================================================
    def get_all_data(self, by_column=False):
        """
        Returns all data in a matrix.  
        """
        all_data = []
        
        # rows (as list) in a list.
        for row in self.entries:
            row_list = []
            for col in self.entries[row]:
                row_list.append(self.entries[row][col].get_value())
            all_data.append(row_list)
                
        if by_column:
            transformed_data = [[] for k in range(len(all_data[0]))]
            for row in self.entries:
                for col in self.entries[row]:
                    transformed_data[col].append(all_data[row][col])
            return transformed_data
        else:
            return all_data

    def insert_values(self, rows, cols, values):
        for row, col, val in zip(rows, cols, values):
            self.entries[row][col].insert(0, val)

    def set_df(self, df, columns=None):
        if columns is not None:
            header = columns
        else:
            header = df.columns

        row_range = list(x+1 for x in range(df.__len__()))
        for col, key in enumerate(header):
            self.insert_values(row_range, [col]*(df.__len__()+1), list(df[key].values))
            # self.set_column_values(col, [key] + list(df[key].values))

    def set_value(self, row, col, value):
        self.entries[row][col].set_value(value)
        
    #===========================================================================
    def set_column_entry_type(self, col, entry_type):
        for row in self.entries:
            self.entries[row][col].set_entry_type(entry_type)
            
    #===========================================================================
    def set_row_entry_type(self, row, entry_type):
        for col in self.entries[row]:
            self.entries[row][col].set_entry_type(entry_type)

    def set_prop(self, column=None, row=None, cell=None, **kwargs):
        if cell:
            self.entries[cell[0]][cell[1]].set_prop(**kwargs)
        elif column:
            for row in self.entries:
                self.entries[row][col].set_prop(**kwargs)
        elif row:
            for col in self.entries[row]:
                self.entries[row][col].set_prop(**kwargs)

    def set_column_values(self, col, value_list=[]):
        """ Fills column with items in given list. Fils untill nr_rows or len(value_list) is reached. """
        for row, value in enumerate(value_list):
            if row in self.entries.keys():
                if row in self.entries and col in self.entries[row]:
                    self.entries[row][col].set_value(value)

    def set_row_values(self, row, value_list=[]):
        """ Fills row with items in given list. Fils untill nr_cols och len(value_list) is reached. """
        for col, value in enumerate(value_list):
            if col in self.entries[row]:
                # print('COL VALUE', row, col, value, self.entries[row][col].frame)
                self.entries[row][col].set_value(value)
        
    #===========================================================================
    def reset_entry(self, row, col, force=False):
        """ If force=True entry in cleard regardless of state. """
        self.entries[row][col].reset_entry(force=force)
        
    #===========================================================================
    def reset_all_entries(self, force=False):
        for row in self.entries:
            for col in self.entries[row]:
                self.reset_entry(row, col, force=force)
        
    #===========================================================================
    def set_width_for_columns(self, col_width={}):
        """ Sets the column width. col_width is a dict with column index as key and width as value """
        for col, value in col_width.items():
            for row in self.entries:
                if col in self.entries[row]:
                    self.entries[row][col].set_prop(width=value)

    #===========================================================================
    def disable_entry(self, row, col):
        self.entries[row][col].set_state('disabled')
    
    #===========================================================================
    def disable_row(self, *row):
        for r in row:
            for col in self.entries[r]:
                self.disable_entry(r, col)
            
    #===========================================================================
    def disable_col(self, *col):
        for row in self.entries:
            for c in col:
                self.disable_entry(row, c)
            
    #===========================================================================
    def enable_entry(self, row, col):
        self.entries[row][col].set_state('normal')
    
    #===========================================================================
    def enable_row(self, row):
        for col in self.entries[row]:
            self.enable_entry(row, col)
            
    #===========================================================================
    def enable_col(self, col):
        for row in self.entries:
            self.enable_entry(row, col)
    


"""
================================================================================
================================================================================
================================================================================
"""
class HoverWindow(object):
    """
    Adds hover ability to a given widget. 
    """
    def __init__(self, 
                 widget, 
                 text='',                 
                 root_window=None, 
                 **kwargs): 
        self.text = text
        self.root_window = root_window
        self.widget = widget 
        self.kwargs = kwargs
        
        widget.bind("<Enter>", self._display)
        widget.bind("<Leave>", self._remove)

    #===========================================================================
    def _display(self, event):
        # Create window 
        self.hover_window = tk.Toplevel(self.root_window)
        self.hover_window.overrideredirect(1) # No border or menu bar
        
        # Set text
        self.label = tk.Label(self.hover_window, text=self.text, bg=self.kwargs.get('bg', 'orange'))
        self.label.pack(side="top", fill="x")
        self.hover_window.update_idletasks() # Needs to be updated to get the size
        
        # Position
        w = self.hover_window.winfo_width()
        h = self.hover_window.winfo_height()  
        mouse_x, mouse_y = self.root_window.winfo_pointerxy()
        self.hover_window.geometry("%dx%d+%d+%d" % (w, h, mouse_x, mouse_y))
        
    
    #===========================================================================
    def _remove(self, event):
        self.hover_window.destroy()
    

"""
================================================================================
================================================================================
================================================================================
"""       
class LabelFrameLabel(tk.LabelFrame):
    """
    Created     20180822     
    """
    
    def __init__(self, 
                 parent, 
                 prop_frame={}, 
                 prop_label={},
                 pack=True, 
                 **kwargs):
        
        # Update kwargs dict
        #---------------------------------------------------------------------------------------
        self.prop_frame = {}
        self.prop_frame.update(prop_frame)
    
                
        
        self.grid_frame = {'row':0, 
                           'column': 0,
                           'sticky': 'nsew',
                           'padx': 0,
                           'pady': 0}
        self.grid_frame.update(kwargs)

        
        #---------------------------------------------------------------------------------------
        tk.Frame.__init__(self, parent, **self.prop_frame)
        if pack:
            self.pack(side="top", fill="both", expand=True)
        else:
            self.grid(**self.grid_frame)
            
        self.stringvar = tk.StringVar()
        self.label = tk.Label(self, textvariable=self.stringvar)
        self.label.grid(row=0, column=0, sticky='nsew')
        grid_configure(self)
        # self.label.pack(side="top", fill="both", expand=True)


    #===========================================================================
    def set_text(self, value, **kwargs): 
        """
        """
        self.reset()
        self.stringvar.set(value)
        self.label.configure(**kwargs)
        self.update_idletasks()
    
    
    #===========================================================================
    def reset(self):
        """
        """ 
        self.stringvar.set('')
        self.label.configure(bg=None, fg='black')
        self.update_idletasks()
    
  
"""
================================================================================
================================================================================
================================================================================
"""       
class ListboxWidget(tk.Frame):
    """
    Created     20180822      
    """
    
    def __init__(self, 
                 parent, 
                 prop_frame={}, 
                 prop_listbox={},
                 items=[], 
                 only_unique_items=True, 
                 include_delete_button=True,
                 callback_delete_button=None,  # returns at the removed item
                 title='',
                 **kwargs):

        self.sort_items = kwargs.pop('sort_items', True)
        self.prop_frame = {}
        self.prop_frame.update(prop_frame)
        
        self.prop_listbox = {'bg': 'grey'}
        self.prop_listbox.update(prop_listbox)        
        
        self.grid_frame = {'row': 0,
                           'column': 0,
                           'sticky': 'nsew',
                           'padx': 5,
                           'pady': 5}
        self.grid_frame.update(kwargs)
        
        self.title = title
        self.items = items
        self.only_unique_items = only_unique_items 
        self.include_delete_button = include_delete_button
        self.callback_delete_button = callback_delete_button
        
        #---------------------------------------------------------------------------------------
        tk.Frame.__init__(self, parent, **self.prop_frame)
        self.grid(**self.grid_frame) 
        
#        grid_configure(self)
            
        self._set_frame()
    
    #===========================================================================
    def _set_frame(self):
        
        padx = 2
        pady = 2
        frame = tk.Frame(self)
        frame.grid(row=0, column=0, padx=padx, pady=pady, sticky='nsew')
        grid_configure(self) 
        
        r=0
        self.listbox = tk.Listbox(frame, selectmode='single', **self.prop_listbox)
        self.listbox.grid(row=r, column=0, padx=padx, pady=pady, sticky='nsew')
        self.scrollbar = ttk.Scrollbar(frame, 
                                       orient='vertical',
                                       command=self.listbox.yview)
        self.scrollbar.grid(row=r, column=1, pady=pady, sticky='nsw')
        self.listbox.configure(yscrollcommand=self.scrollbar.set)
        
        if self.include_delete_button: 
            r+=1
            button_text = 'Delete' 
            if type(self.include_delete_button) == str:
                button_text = self.include_delete_button
            self.button_delete = ttk.Button(frame, text=button_text, command=self._on_delete_item)
            self.button_delete.grid(row=r, column=0, padx=padx, pady=pady, sticky='w')
        
        grid_configure(frame, nr_rows=r+1, nr_columns=2, c0=10) 
        
        
    #===========================================================================
    def add_item(self, item):
        self.items.append(item) 
        self._update_items()
        
        
    #===========================================================================
    def remove_item(self, item):
        if item in self.items:
            self.items.remove(item)
        self._update_items()
        
    #===========================================================================
    def _on_delete_item(self, event=None): 
        selection = self.listbox.curselection()
        if selection:
            index_to_pop = int(selection[0])
            item = self.items[index_to_pop]
            self.items.pop(index_to_pop) 
            self._update_items()
            if self.callback_delete_button:
                self.callback_delete_button(item)
        
    #===========================================================================
    def update_items(self, items=None):
        self.items = items or []
        self._update_items()
    
    #===========================================================================
    def _update_items(self): 
        # Delete old entries
        self.listbox.delete(0, 'end')
        
        if self.only_unique_items:
            self.items = list(set(self.items))
        # Add new entries
        if self.sort_items:
            try:
                self.items = sorted(self.items, key=int)
            except:
                self.items = sorted(self.items)
            
#        if self.include_blank_item: 
#            if u'<blank>' in self.items:
#                self.items.pop(self.items.index(u'<blank>'))
#            self.items = [u'<blank>'] + self.items 
        for item in self.items:  
            self.listbox.insert('end', item)

    def get_items(self):
        return self.items[:]
    
"""
================================================================================
================================================================================
================================================================================
"""       
class ListboxSelectionWidget(tk.Frame):
    """
    Frame to hold widgets for series selection. 
    The class is a frame containing all series selection widgets sepcified in init. 
    Consider using SeriesSelectionWidget() instead. 
    """
    
    def __init__(self, 
                 parent, 
                 prop={}, 
                 prop_frame={}, 
                 prop_items={},
                 prop_selected={}, 
                 items=[], 
                 selected_items=[], 
                 title_items=None,
                 title_selected=None,
                 font=None, 
                 include_button_move_all_items=True, 
                 include_button_move_all_selected=True, 
                 callback_match_in_file=None, 
                 callback_match_subselection=None,
                 callback_set_default=None,
                 callback=None, 
                 callback_select=None, 
                 callback_deselect=None,
                 sort_items=True, 
                 sort_selected=False, 
                 include_blank_item=False,
                 only_unique_items=False,
                 target=None,
                 target_select=None,
                 target_deselect=None, 
                 bind_tab_entry_items=None, 
                 widget_id='',
                 allow_nr_selected=None, 
                 vertical=False,
                 search_case_sensitive=True,
                 count_text='items',
                 multiselect=True,
                 **kwargs):
        
        # Update kwargs dict
        #---------------------------------------------------------------------------------------
        self.prop_frame = {}
        self.prop_frame.update(prop_frame)
        
        if prop:
            prop_items = prop
            prop_selected = prop 
            
        self.prop_listbox_items = {'bg': 'grey',
                                   'width': 30,
                                   'height': 10}
        self.prop_listbox_items.update(prop_items)
        
        self.prop_listbox_selected = {'width': 30,
                                      'height': 10}
        self.prop_listbox_selected.update(prop_selected)

        self.grid_frame = {'row': 0,
                           'column': 0,
                           'sticky': 'nsew',
                           'padx': 5,
                           'pady': 5}
        self.grid_frame.update(kwargs)

        
        #---------------------------------------------------------------------------------------
        tk.Frame.__init__(self, parent, **self.prop_frame)
        self.grid(**self.grid_frame)
        
        self.sort_items = sort_items
        self.sort_selected = sort_selected
        self.only_unique_items = only_unique_items
        self.title_items = title_items
        self.title_selected = title_selected
        self.items = items[:] # List of items to choose from. Copy of list here is very important!
        self.selected_items = selected_items[:] # Copy of list here is very important!
        self.widget_id = widget_id
        self.bind_tab_entry_items = bind_tab_entry_items
        self.allow_nr_selected = allow_nr_selected
        self.vertical = vertical 
        self.search_case_sensitive = search_case_sensitive
        self.count_text = count_text
        if multiselect:
            self.selectmode = 'extended'
        else:
            self.selectmode = 'single'

        self.include_button_move_all_items = include_button_move_all_items
        self.include_button_move_all_selected = include_button_move_all_selected
        
        self.callback_match_in_file = callback_match_in_file
        self.callback_match_subselection = callback_match_subselection
        self.callback_set_default = callback_set_default
        
        if callback:
            self.callback_select = callback
            self.callback_deselect = callback
        else:
            self.callback_select = callback_select
            self.callback_deselect = callback_deselect
        
        if isinstance(target, list):
            self.targets = target
        elif not target:
            self.targets = []
        else:
            self.targets = [target]
            
        self.target_select = target_select
        self.target_deselect = target_deselect
        self.include_blank_item = include_blank_item
        
        # Swich to no it item is selected (moved to selected) or deselected (moved to items)
        # This is so that the right target can be called
        self.last_move_is_selected = True 
        
        if font:
            self.font = font
        else:
            self.font = Fonts().fontsize_medium
        if not self.prop_listbox_items.get('font'):
            self.prop_listbox_items['font'] = self.font
        if not self.prop_listbox_selected.get('font'):
            self.prop_listbox_selected['font'] = self.font
        
        self._remove_selected_items_from_items()
        self._set_frame()

        self._update_listboxes(update_targets=False)
        
    #===========================================================================
    def _set_frame(self):

        self.frame_items = tk.Frame(self)
        self.frame_selected = tk.Frame(self)
        self.frame_buttons = tk.Frame(self)
        
        button_r=1
        c = 0
        self.frame_items.grid(row=0, column=c, sticky='nw')
        if self.vertical:
            self.frame_selected.grid(row=1, column=c, sticky='nw')
            button_r += 1
        else:
            c+=1
            self.frame_selected.grid(row=0, column=c, sticky='nw')

            self.frame_buttons.grid(row=button_r, column=0, sticky='nw')

        grid_configure(self, nr_rows=button_r+1, nr_columns=c+1)

        self._set_frame_items()
        self._set_frame_selected()
        self._set_frame_buttons()

    def _set_frame_items(self):
        frame = self.frame_items
        padx = 5
        pady = 2

        r = 0
        if self.title_items:
            tk.Label(frame, **self.title_items).grid(row=0, column=0)
            r+=1

        self.listbox_items = tk.Listbox(frame, selectmode=self.selectmode, **self.prop_listbox_items)
        self.listbox_items.grid(row=r, column=0, columnspan=2,
                                 sticky='nsew', padx=(padx, 0), pady=pady)
        self.scrollbar_items = ttk.Scrollbar(frame,
                                              orient='vertical',
                                              command=self.listbox_items.yview)
        self.scrollbar_items.grid(row=r, column=2, sticky='ns')
        self.listbox_items.configure(yscrollcommand=self.scrollbar_items.set)
        self.listbox_items.bind('<<ListboxSelect>>', self._on_click_items)
        self.listbox_items.bind('<Double-Button-1>', self._on_doubleclick_items)
        self.listbox_items.bind('<Return>', self._on_return_items)
        r+=1
        
        # Search field items
        self.stringvar_items = tk.StringVar()
        self.entry_items = tk.Entry(frame,
                                    textvariable=self.stringvar_items, 
                                    width=self.prop_listbox_items['width'], 
                                    state='normal')
        self.entry_items.grid(row=r, column=0, columnspan=2, sticky='e')
        self.stringvar_items.trace("w", self._search_item)
        self.entry_items.bind('<Return>', self._on_return_entry_items)
        self.entry_items.bind('<Tab>', self._on_tab_entry_items)
        r+=1
        
        # Information about number of items in list
        self.stringvar_nr_items = tk.StringVar()
        tk.Label(frame, textvariable=self.stringvar_nr_items, font=Fonts().fontsize_small).grid(row=r, column=1, sticky='e')

        if self.include_button_move_all_items:
            self.button_move_all_items = tk.Button(frame, text=u'Select all', command=self._select_all, font=Fonts().fontsize_small)
            self.button_move_all_items.grid(row=r, column=0, padx=padx, pady=pady, sticky='w')
            r+=1

        grid_configure(frame, nr_rows=r, nr_columns=3, r0=10)

    def _set_frame_selected(self):
        frame = self.frame_selected
        padx = 5
        pady = 2

        r = 0
        if self.title_selected:
            tk.Label(frame, **self.title_selected).grid(row=r, column=0)
            r+=1 
            
        self.listbox_selected = tk.Listbox(frame, selectmode=self.selectmode, **self.prop_listbox_selected)
        self.listbox_selected.grid(row=r, column=0, columnspan=2,
                                 sticky='nsew', padx=(padx, 0), pady=pady)
        self.scrollbar_selected = ttk.Scrollbar(frame,
                                              orient='vertical',
                                              command=self.listbox_selected.yview)
        self.scrollbar_selected.grid(row=r, column=2, sticky=u'ns')
        self.listbox_selected.configure(yscrollcommand=self.scrollbar_selected.set)
    #         Hover(self.listbox_series, text=HelpTexts().listbox_seriesinformation, controller=self.controller)
        self.listbox_selected.bind('<<ListboxSelect>>', self._on_click_selected)
        self.listbox_selected.bind('<Double-Button-1>', self._on_doubleclick_selected)
        self.listbox_selected.bind('<Return>', self._on_return_selected)
        r += 1
        
        # Search field selected
        self.stringvar_selected = tk.StringVar()
        self.entry_selected = tk.Entry(frame,
                                    textvariable=self.stringvar_selected, 
                                    width=self.prop_listbox_selected['width'], 
                                    state='normal')
        self.entry_selected.grid(row=r, column=0, columnspan=2, sticky='e')
        self.stringvar_selected.trace("w", self._search_selected)
        self.entry_selected.bind('<Return>', self._on_return_entry_selected)
        r+=1
        
        # Information about number of items in list
        self.stringvar_nr_selected_items = tk.StringVar()
        tk.Label(frame, textvariable=self.stringvar_nr_selected_items, font=Fonts().fontsize_small).grid(row=r, column=1, sticky='e')
        
        if self.include_button_move_all_selected:
            self.button_move_all_selected = tk.Button(frame, text='Deselect all', command=self._deselect_all, font=Fonts().fontsize_small)
            self.button_move_all_selected.grid(row=r, column=0, pady=pady, sticky='w')
            r+=1

        grid_configure(frame, nr_rows=r, nr_columns=3, r0=10)

    def _set_frame_buttons(self):
        frame = self.frame_buttons
        padx = 5
        pady = 2

        r = 0
        if self.callback_match_in_file:
            self.button_match_in_file = tk.Button(frame, text=u'Match in file', command=self.callback_match_in_file, font=Fonts().fontsize_small)
            self.button_match_in_file.grid(row=r, column=0, padx=padx, pady=pady, sticky='w')
            r += 1

        if self.callback_match_subselection:
            self.button_match_subselection = tk.Button(frame, text='Match subselection', command=self.callback_match_subselection, font=Fonts().fontsize_small)
            self.button_match_subselection.grid(row=r, column=0, padx=padx, pady=pady, sticky='w')
            r += 1

        if self.callback_set_default:
            self.button_select_default = tk.Button(frame, text='Select default',
                                                       command=self.callback_set_default,
                                                       font=Fonts().fontsize_small)
            self.button_select_default.grid(row=r, column=0, padx=padx, pady=pady, sticky='w')
            r += 1

        grid_configure(frame, nr_rows=r)
    
    #===========================================================================
    def _on_tab_entry_items(self, event):
        if self.bind_tab_entry_items:
            self.bind_tab_entry_items()
        
    #===========================================================================
    def _remove_selected_items_from_items(self):
        for selected in self.selected_items:
            if selected in self.items:
                self.items.pop(self.items.index(selected))
        
    #===========================================================================
    def add_target(self, target):
        self.targets.append(target)

    def _select_all(self):
        self.select_all()
        if self.callback_select:
            self.callback_select()

    def _deselect_all(self):
        self.deselect_all()
        if self.callback_deselect:
            self.callback_deselect()

    def select_all(self):
        self.selected_items.extend(self.items)
        self.items = []
        self.stringvar_items.set(u'')
        self._update_listboxes()
    
    #===========================================================================
    def deselect_all(self):
        self.items.extend(self.selected_items)
        self.selected_items = []
        self.stringvar_selected.set(u'')
        self._update_listboxes()
    
    #===========================================================================
    def delete_selected(self):
        self.selected_items = []
        self.last_move_is_selected = False
        self._update_listboxes()
        
    #===========================================================================
    def clear_lists(self):
        self.update_items()
        
    #===========================================================================
    def add_items(self, items, move_to_selected=False):
        """ 
        Add items to self.items. 
        If "move_to_selected"=True the items are moved to selected. 
        """  
        for item in items:
            # First check if item already present
            if item in self.items or item in self.selected_items:
                continue
            self.items.append(item)
        
        if move_to_selected:
            self.move_items_to_selected(items)
            
        self._update_listboxes(update_targets=False)
        
    #===========================================================================
    def delete_items(self, items):
        """ Deletes items from widget """
        for item in items:
            if item in self.items:
                self.items.pop(self.items.index(item))
            elif item in self.selected_items:
                self.selected_items.pop(self.selected_items.index(item))
        self._update_listboxes(update_targets=False)
            
    #===========================================================================
    def update_items(self, items=[], keep_selected=False):
        """ 
        Resets the listbox and updates it with given items. 
        If no items are given, all items in widget will be removed. 
        If "keep_selected"==True selected items will be still selected if they belong to the new item list.
        """
        if items in [None, False]:
            logger.debug(f'Items is set to {items}. Converting to list!')
            items = []
        items = items or []
        selected_items = self.get_selected()
        self.items = items[:]
        self.selected_items = []
        self._update_listboxes(update_targets=False)
        
        if keep_selected:
            self.move_items_to_selected(selected_items, update_targets=False)
        
    #===========================================================================
    def _move_to_selected(self, item=None, index=None):
        """ Moves given item from self.items to self.selected_items list if allowed by self.allow_nr_selected """
        if item and item not in self.items:
            return
        
        if item != None:
            i = self.items.index(item)
        elif index != None:
            i = index
        
        if not self.allow_nr_selected or len(self.selected_items) < int(self.allow_nr_selected):
            selected_item = self.items.pop(i)
            self.selected_items.append(selected_item)
        else:
            # Replace the last item in self.selected_items 
            item = self.selected_items.pop(-1)
            self.items.append(item)
            
            selected_item = self.items.pop(i)
            self.selected_items.append(selected_item)

    def move_items_to_selected(self, items, update_targets=False):
        if type(items) != list:
            items = [items]
        for item in items:
            if item in self.items:
                self._move_to_selected(item=item)
        self.last_move_is_selected = True
        self._update_listboxes(update_targets=update_targets)

    def move_selected_to_items(self, items, update_targets=False):
        if type(items) != list:
            items = [items]
        for item in items:
            if item in self.selected_items:
                self.items.append(self.selected_items.pop(self.selected_items.index(item)))
        self.last_move_is_selected = False
        self._update_listboxes(update_targets=update_targets)

    def _update_listboxes(self, update_targets=True):
        self._update_listbox_items()
        self._update_listbox_selected()  

        nr_items = f'{len(self.items)} {self.count_text}'
        nr_selected_items = f'{len(self.selected_items)} {self.count_text}'
        self.stringvar_nr_items.set(nr_items)
        self.stringvar_nr_selected_items.set(nr_selected_items)
        
        if update_targets:
            if self.targets:
                for target in self.targets:
                    # print(target)
                    target()
            
            if self.target_select and self.last_move_is_selected:
                self.target_select() 
                 
            if self.target_deselect and not self.last_move_is_selected:
                self.target_deselect()

            if self.callback_select and self.last_move_is_selected:
                self.callback_select()

            if self.callback_deselect and not self.last_move_is_selected:
                self.callback_deselect()

    def _search_item(self, *dummy):
        if self.selectmode == 'single':
            return
        self.listbox_items.selection_clear(0, 'end')
        search_string = self.stringvar_items.get().strip()
        if not search_string:
            return
        if not self.search_case_sensitive:
            search_string = search_string.lower()
        index = []
        for i, item in enumerate(self.items):
            if not self.search_case_sensitive:
                item = item.lower()
            if search_string in item:
                index.append(i)
        if not index:
            return
        for i in index:
            self.listbox_items.selection_set(i)
            self.listbox_items.see(i)

    def _search_selected(self, *dummy):
        if self.selectmode == 'single':
            return
        self.listbox_selected.selection_clear(0, 'end')
        search_string = self.stringvar_selected.get().strip()
        if not search_string:
            return
        if not self.search_case_sensitive:
            search_string = search_string.lower()
        index = []
        for i, item in enumerate(self.selected_items):
            if not self.search_case_sensitive:
                item = item.lower()
            if search_string in item:
                index.append(i)
        if not index:
            return
        for i in index:
            self.listbox_selected.selection_set(i)
            self.listbox_selected.see(i)

    def _on_return_entry_items(self, event):
        self._search_item(None)
        self._on_return_items(None)
#         search_string = self.stringvar_items.get().lower()
#         index = []
#         for i, item in enumerate(self.items):
#             if search_string and item.lower().startswith(search_string):
#                 index.append(i)
#         if len(index) >= 1:
#             for i in index[::-1]:
#                 self._move_to_selected(index=i)
# #                 selected_item = self.items.pop(i)
# #                 self.selected_items.append(selected_item)
#             self.last_move_is_selected = True
#             self._update_listboxes()
#             self.stringvar_items.set(u'')
#         if self.callback_select:
#             self.callback_select()

    def _on_return_entry_selected(self, event):
        self._search_selected(None)
        self._on_return_selected(None)
        # search_string = self.stringvar_selected.get().lower()
        # index = []
        # for i, item in enumerate(self.selected_items):
        #     if search_string and item.lower().startswith(search_string):
        #         index.append(i)
        # if len(index) >= 1:
        #     for i in index[::-1]:
        #         selected_item = self.selected_items.pop(i)
        #         self.items.append(selected_item)
        #     self.last_move_is_selected = False
        #     self._update_listboxes()
        #     self.stringvar_selected.set(u'')
        # if self.callback_deselect:
        #     self.callback_deselect()

    def _on_click_items(self, event):
        if self.selectmode != 'single':
            return
        selection = self.listbox_items.curselection()
        if selection:
            self.stringvar_items.set(self.listbox_items.get(selection[0]))

    def _on_return_items(self, event):
        if self.selectmode != 'extended':
            return
        index = self.listbox_items.curselection()
        if not index:
            return
        items = [self.listbox_items.get(i) for i in index]
        self.move_items_to_selected(items)
        self.listbox_items.see(max(0, max(index)))
        self.stringvar_items.set('')
        self.last_move_is_selected = True
        if self.callback_select:
            self.callback_select()

    def _on_click_selected(self, event):
        if self.selectmode != 'single':
            return
        selection = self.listbox_selected.curselection()
        if selection:
            self.stringvar_selected.set(self.listbox_selected.get(selection[0]))

    def _on_return_selected(self, event):
        if self.selectmode != 'extended':
            return
        index = self.listbox_selected.curselection()
        if not index:
            return
        items = [self.listbox_selected.get(i) for i in index]
        self.move_selected_to_items(items)
        self.listbox_selected.see(max(0, max(index)))
        self.stringvar_selected.set('')
        self.last_move_is_selected = False
        # if self.callback_deselect:
        #     self.callback_deselect()

    def _on_doubleclick_items(self, event):
        selection = self.listbox_items.curselection()
        if selection:
            index_to_pop = int(selection[0])
            self._move_to_selected(index=index_to_pop)
            self.last_move_is_selected = True
            self._update_listboxes()
            self.stringvar_items.set('')
            self.listbox_items.see(max(0, index_to_pop))
        # if self.callback_select:
        #     self.callback_select()

    def _on_doubleclick_selected(self, event):
        selection = self.listbox_selected.curselection()
        if selection:
            index_to_pop = int(selection[0])
            selected_item = self.selected_items.pop(index_to_pop)
            if selected_item != '<blank>':
                self.items.append(selected_item)
            self.last_move_is_selected = False
            self._update_listboxes()
            self.stringvar_selected.set(u'')
            self.listbox_items.see(max(0, index_to_pop))
        if self.callback_deselect:
            self.callback_deselect()
    
    #===========================================================================
    def _update_listbox_items(self): 
        # Delete old entries
        self.listbox_items.delete(0, 'end')
        # Add new entries
        if self.only_unique_items:
            self.items = list(set(self.items))
        # Add new entries
        if self.sort_items:
            try:
                self.items = sorted(self.items, key=int)
            except:
                self.items = sorted(self.items)
        # try:
        #     self.items = sorted(self.items, key=int)
        # except:
        #     self.items = sorted(self.items)
            
        if self.include_blank_item: 
            if '<blank>' in self.items:
                self.items.pop(self.items.index('<blank>'))
            self.items = ['<blank>'] + self.items 
        for item in self.items:  
            self.listbox_items.insert('end', item) 
    
    #===========================================================================
    def _update_listbox_selected(self): 
        # Delete old entries
        self.listbox_selected.delete(0, u'end')
        # Add new entries
        if self.only_unique_items:
            self.selected_items = list(set(self.selected_items))
        # Add new entries
        if self.sort_items:
            try:
                self.selected_items = sorted(self.selected_items, key=int)
            except:
                self.selected_items = sorted(self.selected_items)
        # if self.sort_selected:
        #     try:
        #         self.selected_items = sorted(self.selected_items, key=int)
        #     except:
        #         self.selected_items = sorted(self.selected_items)
        for item in self.selected_items:
            self.listbox_selected.insert('end', item)  
     
    #===========================================================================
    def get_items(self):
        return self.items[:]

    def get_value(self):
        """
        returns selected items as a list.
        :return:
        """
        return self.get_selected()

    def set_value(self, values, **kwargs):
        """
        First deselect all. Then moves "values" to selected.
        :return:
        """
        self.deselect_all()
        self.move_items_to_selected(values, **kwargs)
         
    #===========================================================================
    def get_selected(self):
        return self.selected_items[:]   
         
    #===========================================================================
    def get_all_items(self):
        return sorted(self.get_items() + self.get_selected())

    #===========================================================================
    def set_prop_items(self, **prop):
        self.listbox_items.config(**prop)
        
    #===========================================================================
    def set_prop_selected(self, **prop):
        self.listbox_selected.config(**prop)
        
        
"""
================================================================================
================================================================================
================================================================================
"""
class ListboxSelectionWidgetMultiple(tk.Frame):
    """
    Class to hold several listbox widgets.         
    """
    def __init__(self, 
                 parent, 
                 titles=[], 
                 items={}, 
                 default_prop_items={}, 
                 default_prop_selected={},
                 prop_frame={}, 
                 prop_items={}, 
                 prop_selected={},
                 prop_items_keys={}, 
                 prop_selected_keys={},
                 grid_frame={}, 
                 callback_button=None, 
                 callback_button_name=u'Load', 
                 callback_on_select=None, 
                 callback_on_select_matching=None, 
                 callback_update=None, 
                 notebook_layout=False):
        
        self.parent_frame = parent
        
        self.titles = titles
        self.items = items
        
        self.callback_button = callback_button
        self.callback_button_name = callback_button_name
        self.callback_on_select = callback_on_select
        self.callback_on_select_matching = callback_on_select_matching
        self.callback_update = callback_update
        
        self.notebook_layout = notebook_layout
        
        # Update kwargs and props 
        #---------------------------------------------------------------------------------------
        self.prop_frame = {}
        self.prop_frame.update(prop_frame)
        
        self.prop_items = dict((title, default_prop_items.copy()) for title in titles)
        [self.prop_items[title].update(prop_items[title]) for title in titles if title in self.prop_items and title in prop_items]
         
        self.prop_selected = dict((title, default_prop_selected.copy()) for title in titles)
        [self.prop_selected[title].update(prop_selected[title]) for title in titles if title in self.prop_selected and title in prop_selected]
        
        
        self.prop_items_key = default_prop_items.copy()
        self.prop_items_key.update({'bg':'gray', 
                                    'width':30})
        self.prop_items_key.update(prop_items_keys)
                                   
                                   
        self.prop_selected_key = default_prop_selected.copy()
        self.prop_selected_key.update({'bg':'green', 
                                       'width':30})
        self.prop_selected_key.update(prop_selected_keys)
        
#         self.prop_items = {}
#         self.prop_items.update(default_prop_items)
#         
#         self.prop_selected = {}
#         self.prop_selected.update(default_prop_selected)
#         
#         self.individual_prop_frame = prop_frame
#         self.individual_prop_items = prop_items
#         self.individual_prop_selected = prop_selected
        
        
        self.grid_frame = {'row':0, 
                           'column':0, 
                           'sticky':'nsew', 
                           'padx':5, 
                           'pady':5}
        self.grid_frame.update(grid_frame) 
        
        
        self.grid_labelframes = {'sticky':'nsew', 
                             'padx':5, 
                             'pady':5}
        
        
        #---------------------------------------------------------------------------------------
        # Setup frame
        tk.Frame.__init__(self, parent, **self.prop_frame)
        self.grid(**self.grid_frame)
        
        self._set_frame()
        self._set_labelframes()
        self._set_labelframe_matching_keys()
        self.update_items(self.items)
        
    #===========================================================================
    def _set_frame(self):
        
        # Set up notebook if this layout is selected
        if self.notebook_layout:
            self.notebook = NotebookWidget(self, frames=self.titles + ['Matching keys'])
            
            if self.callback_button:
                padx=5
                pady=5 
                self.button_load_advanced = tk.Button(self, 
                                                text=self.callback_button_name,   
                                                command=self.callback_button)
                self.button_load_advanced.grid(row=1, column=0, sticky=u'sw', columnspan=2, padx=padx, pady=pady)

        else:
            padx=5
            pady=5 
            r=0
            c=0
            self.labelframes = {}
            for title in self.titles:
                self.labelframes[title] = ttk.Labelframe(self, text=title)
                self.labelframes[title].grid(row=r, column=c, **self.grid_labelframes)
                c+=1
            
            c=0
            r+=1
            self.button_clear_selection = tk.Button(self, 
                                            text=u'Clear selection',   
                                            command=self._clear_all_selections)
            self.button_clear_selection.grid(row=r, column=c, sticky=u'nw', columnspan=2, padx=padx, pady=pady)
            
            if self.callback_update:
                self.button_clear_selection = tk.Button(self, 
                                                text=u'Update',   
                                                command=self.callback_update)
                self.button_clear_selection.grid(row=r, column=c+1, sticky=u'nw', columnspan=2, padx=padx, pady=pady)
            r+=1
            
            c=0
            r+=1
            self.labelframe_matching_keys = ttk.Labelframe(self, text=u'Matching keys')
            self.labelframe_matching_keys.grid(row=r, column=c, columnspan=2, **self.grid_labelframes)
            c+=2
            
            if self.callback_button:
                self.button_callback = tk.Button(self, 
                                                text=self.callback_button_name,   
                                                command=self.callback_button)
                self.button_callback.grid(row=r, column=c, sticky=u'sw', columnspan=2, padx=padx, pady=pady)
                r+=1
        
        grid_configure(self)
        
        
#         self._set_labelframe_year()
#         self._set_labelframe_ship()
#         self._set_labelframe_series()
#         self._set_labelframe_project()
#         self._set_labelframe_orderer()
#         self._set_labelframe_matching_keys()
        
    #===========================================================================
    def _set_labelframes(self):
        
        self.listboxes = {}
        
        for title in self.titles:
            if self.notebook_layout: 
                frame = self.notebook.get_frame(title)
            else:
                frame = self.labelframes[title]
                
            self.listboxes[title] = ListboxSelectionWidget(frame, 
                                                           prop_items=self.prop_items[title], 
                                                           prop_selected=self.prop_selected[title], 
                                                           target=self.callback_on_select, 
        #                                                    target_select=self._on_listbox_update_select,
        #                                                    target_deselect=self._on_listbox_update_deselect, 
                                                           sort_selected=True, 
                                                           widget_id=title)
        
        
    
        
    #===========================================================================
    def _set_labelframe_matching_keys(self):
        if not self.callback_on_select:
            return
        
        if self.notebook_layout: 
            frame = self.notebook.frame_matching_keys
        else:
            frame = self.labelframe_matching_keys
        
        self.listbox_matching_keys = ListboxSelectionWidget(frame, 
                                                            prop_items=self.prop_items_key, 
                                                            prop_selected=self.prop_selected_key, 
                                                            sort_selected=True, 
                                                            widget_id=u'keys', 
                                                            target=self.callback_on_select_matching)
    
    #===========================================================================
    def update_items(self, items, keep_selected=True):
        """
        Items are given as a dict.
        """
        for title in self.titles:
            if title not in items:
                continue
            self.listboxes[title].update_items(items[title], keep_selected=keep_selected)
        
        if self.callback_on_select:
            try:
                self.callback_on_select()
            except:
                print('Could not call "callback_on_select()" in ListboxSelectionWidgetMultiple.update_items')
        
    #===========================================================================
    def update_matching(self, items, keep_selected=True):
        """
        Items are given as a list.
        """
        self.listbox_matching_keys.update_items(items, keep_selected=keep_selected)        
                 
    #===========================================================================
    def _clear_all_selections(self):
        for title in self.titles:
            self.listboxes[title].deselect_all() 
        self.listbox_matching_keys.update_items([])    
          
    #===========================================================================
    def reset_all(self):
        for title in self.titles:
            self.listboxes[title].update_items([])
        self.listbox_matching_keys.update_items([])
        
    #===========================================================================
    def get_selected(self):
        selected_dict = {}
        for title in self.titles:
            selected_dict[title] = self.listboxes[title].get_selected()
        
        selected_dict['Matching keys'] = self.listbox_matching_keys.get_selected()
        
        return selected_dict
    
    #===========================================================================
    def get_all_items(self):
        all_dict = {}
        for title in self.titles:
            all_dict[title] = self.listboxes[title].get_all_items()
        
        all_dict['Matching keys'] = self.listbox_matching_keys.get_all_items()
        
        return all_dict
    
    #===========================================================================
    def set_prop_matching_key_selected(self, **prop):
        self.listbox_matching_keys.set_prop_selected(**prop)
                                     
"""
================================================================================
================================================================================
================================================================================
"""
class NotebookWidget(ttk.Notebook):
     
    def __init__(self, 
                 parent, 
                 frames=[], 
                 notebook_prop={},
                 place=(),
                 **kwargs):
        
        self.frame_list = frames
        self.notebook_prop = {}
        self.notebook_prop.update(notebook_prop)
        
        self.grid_notebook = {'padx': 5, 
                              'pady': 5, 
                              'sticky': 'nsew'}
        self.grid_notebook.update(kwargs)
        
        ttk.Notebook.__init__(self, parent, **self.notebook_prop)
        if place:
            self.place(relx=place[0], rely=place[1], anchor=tk.CENTER)
        else:
            self.grid(**self.grid_notebook)
        
        self.frame_dict = {}
        self._set_frame()
        
    def __call__(self, tab):
        """ Returnf a referens to the frame with the provided name"""
        return self.frame_dict.get(tab)
        
    #===========================================================================
    def _set_frame(self):
                
        for frame in self.frame_list:
            name = frame.strip(u'?')
            name = u'frame_' + name.lower().replace(u' ', u'_').replace('ä', 'a').replace('å', 'a').replace('ö', 'o')
            notebook_frame = tk.Frame(self)
            setattr(self, name, notebook_frame)
            self.add(notebook_frame, text=frame)
            self.frame_dict[frame] = notebook_frame
#            grid_configure(self.frame_dict[frame]) # Done when setting frame content
            grid_configure(notebook_frame)
        grid_configure(self)          
    
    #===========================================================================
    def select_frame(self, frame):
        if frame in self.frame_dict:
            self.select(self.frame_dict[frame])
            return True
        else:
            return False

    def get_selcted_tab(self):
        return self.tab(self.select(), "text")

    #===========================================================================
    def get_frame(self, frame):
        return self.frame_dict[frame]
    
    def set_state(self, state, *args, rest=None):
        if rest:
            for frame in self.frame_list:
                self.tab(self.frame_dict[frame], state=rest)
        if not args:
            args = self.frame_list
        for frame in args:
            self.tab(self.frame_dict[frame], state=state)

"""
================================================================================
================================================================================
================================================================================
"""
class PlotFrame(tk.Frame):
    
    #===========================================================================
    def __init__(self, 
                 parent, 
                 plot_object, 
                 prop_frame={}, 
                 include_toolbar=True, 
                 pack=True, 
                 **kwargs):
        
        self.plot_object = plot_object
        self.fig = self.plot_object.fig
        
        self.include_toolbar = include_toolbar
        
        self.prop_frame = {}
        self.prop_frame.update(prop_frame)
        
        self.grid_frame = {'padx': 5, 
                           'pady': 5, 
                           'sticky': 'nsew'}
        self.grid_frame.update(kwargs)
        
        tk.Frame.__init__(self, parent, **self.prop_frame) 
        
        if pack:
            self.pack(side="top", fill="both", expand=True)
        else:
            self.grid(**self.grid_frame)
            grid_configure(self)
            
        self._set_frame()
        
        self.plot_object.add_target(self.update_canvas)
        
        
    #===========================================================================
    def _set_frame(self):
        self.frame_plot = tk.Frame(self)
        self.frame_plot.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        # grid_configure(self.frame_plot)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame_plot)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        if self.include_toolbar:
            self.frame_toolbar = tk.Frame(self)
            self.frame_toolbar.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
            self.toolbar = NavigationToolbar2Tk(self.canvas, self.frame_toolbar)
            self.toolbar.update()
            self.canvas._tkcanvas.pack()
            
    
    #========================================================================== 
    def update_canvas(self):
        self.canvas.draw()


class LogWidget(object):
    """
    """
    def __init__(self, controller, popup_window=False):
        self.controller = controller
        self.popup_window = popup_window

    def display(self):
        padx = 5
        pady = 5

        self.popup_frame = tk.Toplevel(self.controller)
        x = self.controller.winfo_x()
        y = self.controller.winfo_y()

        # Set text
        self.label = tk.Label(self.popup_frame, text=self.text)
        self.label.grid(row=0, column=0, columnspan=2, padx=padx, pady=pady)

        self.entry = tkw.EntryWidget(self.popup_frame, entry_type='int')

        button_ok = tk.Button(self.popup_frame, text='Ok', command=self._ok)
        button_ok.grid(row=1, column=0, padx=padx, pady=pady)

        tkw.grid_configure(self.popup_frame, nr_columns=2, nr_rows=2)

        self.popup_frame.update_idletasks()

        root_dx = self.controller.winfo_width()
        root_dy = self.controller.winfo_height()

        dx = int(root_dx/3)
        dy = int(root_dy/3)
        w = self.popup_frame.winfo_width()
        h = self.popup_frame.winfo_height()
        self.popup_frame.geometry("%dx%d+%d+%d" % (w, h, x + dx, y + dy))
        # self.controller.withdraw()

    def _ok(self):
        if self.entry.get_value():
            self.popup_frame.destroy()
        # self.controller.deiconify()

"""
================================================================================
================================================================================
================================================================================
"""
class MapFrame(tk.Frame):
    
    #===========================================================================
    def __init__(self, 
                 parent, 
                 map_object, 
                 prop_frame={}, 
                 include_toolbar=True, 
                 **kwargs):
        
        self.map_object = map_object
        self.fig = self.map_object.fig
        
        self.include_toolbar = include_toolbar
        
        self.prop_frame = {}
        self.prop_frame.update(prop_frame)
        
        self.grid_frame = {'padx': 5, 
                           'pady': 5, 
                           'sticky': 'nsew'}
        self.grid_frame.update(kwargs)
        
        tk.Frame.__init__(self, parent, **self.prop_frame)
        self.grid(**self.grid_frame)
            
        self._set_frame()
        
        self.map_object.add_target(self.update_canvas)
        
    #===========================================================================
    def _set_frame(self):
        
        self.frame_plot = tk.Frame(self)
        self.frame_plot.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        grid_configure(self.frame_plot)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame_plot)
        self.canvas.show()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        if self.include_toolbar:
            self.toolbar = NavigationToolbar2TkAgg(self.canvas, self.frame_plot)
            self.toolbar.update()
            self.canvas._tkcanvas.pack()
        
        grid_configure(self)
    
    #========================================================================== 
    def update_canvas(self):
        self.canvas.draw()


class ProgressbarWidget(tk.Frame):
    def __init__(self,
                 parent,
                 prop_frame={},
                 bar_length=100,
                 in_rows=False,
                 **kwargs):

        self.bar_length = bar_length

        self.prop_frame = {}
        self.prop_frame.update(prop_frame)
        self.in_rows = in_rows

        self.grid_frame = {'padx': 5,
                           'pady': 5,
                           'sticky': 'nsew'}
        self.grid_frame.update(kwargs)

        tk.Frame.__init__(self, parent, **self.prop_frame)
        self.grid(**self.grid_frame)

        self._set_frame()

    def _set_frame(self):
        padx = 2
        pady = 0

        self.stringvar_text = tk.StringVar()
        self.text = tk.Label(self, textvariable=self.stringvar_text)
        if self.in_rows:
            self.text.grid(row=0, column=0, padx=padx, pady=pady)
            grid_configure(self, nr_rows=2)
        else:
            self.text.grid(row=0, column=0, padx=padx, pady=pady, sticky='w')
            grid_configure(self, nr_columns=2)

        self.progress = ttk.Progressbar(self, orient=tk.HORIZONTAL, length=self.bar_length, mode='indeterminate')

    def run_progress(self, run_function, message='', **kwargs):
        self.stringvar_text.set(message)
        if self.in_rows:
            self.progress.grid(row=1, column=0)
            grid_configure(self, nr_rows=2)
        else:
            self.progress.grid(row=0, column=1, sticky='e')
            grid_configure(self, nr_columns=2)
        self.progress.start()
        run_function()
        self.progress.stop()
        self.progress.grid_forget()
        self.stringvar_text.set('')



"""
================================================================================
================================================================================
================================================================================
"""
class RadiobuttonWidget(tk.Frame):
     
    def __init__(self, 
                 parent, 
                 items=[], 
                 prop_frame={}, 
                 default_item=None,
                 nr_rows_per_column=10, 
                 map_target=None,
                 target=None,  
                 update_on_selection=True, 
                 colors={}, 
                 **kwargs):
        
        self.prop_frame = {}
        self.prop_frame.update(prop_frame)
        
        self.grid_frame = {'padx': 5, 
                           'pady': 5, 
                           'sticky': 'nsew'}
        self.grid_frame.update(kwargs)
        
        tk.Frame.__init__(self, parent, **self.prop_frame)
        self.grid(**self.grid_frame)
        
        self.items = items 
        self.default_item = default_item 
        self.nr_rows_per_column = nr_rows_per_column 
        self.map_target = map_target 
        self.target = target
        self.update_on_selection = update_on_selection 
        self.colors = colors
        
        self.rbutton = {}
        
        self._set_frame()
        
        
    #===========================================================================
    def _set_frame(self):
        padx = 2
        pady = 0
        
        frame = tk.Frame(self)
        frame.grid(row=0, column=0, padx=padx, pady=pady, sticky='w')
        grid_configure(self) 
        
        nr_rows = 0
         
        r=0
        c=0

        self.stringvar = tk.StringVar()
        for item in self.items:
            self.rbutton[item] = tk.Radiobutton(frame, 
                                              text=item,  
                                              value=item, 
                                              variable=self.stringvar, 
                                              command=self._on_select)
            self.rbutton[item].grid(row=r, column=c, sticky=u'w', padx=padx, pady=pady)
            if item in self.colors:
                self.rbutton[item].config(fg=self.colors[item])
            r+=1
            if not r%self.nr_rows_per_column:
                c+=1
                r=0
            if r > nr_rows:
                nr_rows = r
            self.rbutton[item].bind() 
            
        grid_configure(frame, nr_rows=nr_rows)
        
        if self.default_item:
            self.stringvar.set(self.default_item)
    
    
    #===========================================================================
    def _on_select(self):
        if self.map_target and self.update_on_selection:
            self.map_target.update_map()
        elif self.target:
            # target is a direct link to a function och method (not class)
            self.target()


    #===========================================================================
    def get(self):
        return self.stringvar.get()

    # ===========================================================================
    def get_value(self):
        return self.stringvar.get()
    
    #===========================================================================
    def set(self, value):
        try:
            self.stringvar.set(value)
        except:
            pass

    # ===========================================================================
    def set_value(self, value):
        self.set(value)
        
    #===========================================================================
    def change_color(self, item, new_color):
        self.rbutton[item].config(fg=new_color)
        
"""
================================================================================
================================================================================
================================================================================
"""
class SelectionWidgets(tk.Frame):
    """
    Class to hold widgets for series selection. entries for selections.
    """
    
    def __init__(self, 
                 parent, 
                 field_list=[], 
                 expect_string=[], 
                 prop_frame={},  
                 **kwargs):
        
        self.grid_frame = {}
        self.grid_frame.update(**kwargs)
        
        self.prop_frame = {}
        self.prop_frame.update(**prop_frame)
        
        tk.Frame.__init__(self, parent, **self.prop_frame)
        self.grid(**self.grid_frame)
        
        self.field_list = field_list
        self.expect_string = expect_string

        self.widget_list = []
        self.target_list = [] # Holds list of all target that will be called from self._get_selection()
        
        self._set_frame()
        
        grid_configure(self)

    #===========================================================================
    def _set_frame(self):
        
        padx = 5
        pady = 5
        
        r = 0
        c = 0
        
        self.stringvar = {}
        self.entry = {}
        #-------------------------------------------------------------------------
        if self.field_list:
            for item in self.field_list:
                ttk.Label(self, text=item).grid(row=r, column=c, sticky=u'w', padx=padx, pady=pady)
                self.stringvar[item] = tk.StringVar()
                self.entry[item] = tk.Entry(self, 
                                            textvariable=self.stringvar[item], 
                                            width=10)
                self.entry[item].grid(row=r, column=c+1, sticky=u'w', padx=padx, pady=pady)
                r+=1
                
                self.entry[item].bind("<Return>", lambda event, item=item: self._focus_next_entry(self.entry[item]))
                self.widget_list.append(self.entry[item])   
              
              
    #===========================================================================
    def _focus_next_entry(self, current_widget): 
        index = self.widget_list.index(current_widget)
        if index == len(self.widget_list)-1:
            new_index = 0
        else:
            new_index = index + 1
        self.widget_list[new_index].configure(state=u'normal')
        self.widget_list[new_index].select_range(0, u'end')
        self.widget_list[new_index].focus_set()
        
    #===========================================================================
    def get_value(self, key, pad_zeroes=False):
        if key not in self.stringvar:
            print(u'Unvalid key in SelectionWidgets.get_value(self, key)')
#             Log().note(u'Unvalid key in SelectionWidgets.get_value(self, key)')
            return
        if key in self.expect_string:
            value_list = self._get_list_from_entry(stringvar=self.stringvar[key], expect_string=True)
            if not value_list[0]: return None
        else:
            value_list = self._get_list_from_entry(stringvar=self.stringvar[key])
        if not value_list:
            return None
        if pad_zeroes:
            new_list = []
            for value in value_list:
                new_value = value.rjust(pad_zeroes, u'0')
                new_list.append(new_value)
            value_list = new_list
        return value_list
    
    #===========================================================================
    def _get_list_from_entry(self, stringvar=None, string=None, expect_string=False):
        try:
            output_list = []
            if stringvar:
                string = stringvar.get().strip()
            split_string = string.split(u',')
            for item in split_string:
                split_item = item.split(u'-')
                if len(split_item) == 2: 
                    if not split_item[0].strip(): # Empty string, search from mean
                        start_value = 1
                    else:
                        start_value = int(split_item[0].strip())
                    stop_value = int(split_item[1].strip())
                    if stop_value == start_value:
                        output_list.append(start_value)
                    elif stop_value > start_value:
                        for value in range(start_value, stop_value+1):
                            if value not in output_list:
                                output_list.append(value)
                else:
                    if expect_string: 
                        value = split_item[0].strip()
                    else:
                        value = int(split_item[0].strip())
                    # value = split_item[0].strip()
                    if value not in output_list:
                        output_list.append(value)
            output_list = sorted(output_list)
            return map(str, output_list)
        except:
            return None



      



"""
================================================================================
================================================================================
================================================================================
"""
class TextScrollbarWidget(tk.Frame):   
    """
    Combines tk.Text and tk.Scrollbars. 
    Option to:
        set height and width
        include vertical scrollbar
        include horizontal scrollbar
    """
    def __init__(self, 
                 parent,
                 height=10,
                 width=40,  
                 prop_frame={}, 
                 font=None, 
                 include_vertical_scrollbar=True, 
                 include_horizontal_scrollbar=True, 
                 pack=True, 
                 editable=False, 
                 **kwargs):
        
        self.prop_frame = {}
        self.prop_frame.update(prop_frame)
        
        self.grid_frame = {'padx': 5, 
                           'pady': 5, 
                           'sticky': 'nsew'}
        self.grid_frame.update(kwargs)
        
        tk.Frame.__init__(self, parent, **self.prop_frame)
        if pack:
            self.pack(side="top", fill="both", expand=True)
        else:
            self.grid(**self.grid_frame)
            
        self.height = height
        self.width = width
        self.pack = pack
        
        if editable:
            self.state = 'normal'
        else:
            self.state = 'disabled'
        
        self.font = font
        
        self.include_vertical_scrollbar = include_vertical_scrollbar
        self.include_horizontal_scrollbar = include_horizontal_scrollbar
        
        self._set_frame()
        
    #===========================================================================
    def _set_frame(self):
        
        if self.pack:
            frame = tk.Frame(self)
            frame2 = tk.Frame(self)
            ys = tk.Scrollbar(frame)
            xs = tk.Scrollbar(frame2)
            self.text = tk.Text(frame, yscrollcommand=ys.set, xscrollcommand=xs.set, wrap='none', font=self.font)
            xs.config(orient='hor', command=self.text.xview)
            ys.config(orient='vert', command=self.text.yview)
            ys.pack(side='right', expand=False, fill='y')
            self.text.pack(side='left', expand=True, fill='both')
            frame.pack(side='top',expand=True,fill='both')
            frame2.pack(side='top',fill='x')
            tk.Frame(frame2).pack(side='left')
            xs.pack(side='left',expand=True,fill='x')
        
        else:
            self.text = tk.Text(self, wrap='none', width=self.width, height=self.height, font=self.font)
            self.text.grid(row=0, column=0, sticky=u'nsew')
              
            if self.include_vertical_scrollbar:
                self.scrollbar_y = ttk.Scrollbar(self, 
                    orient=u'vertical', command=self.text.yview)
                self.scrollbar_y.grid(row=0, column=1, sticky=u'nsew') 
                self.text.configure(yscrollcommand=self.scrollbar_y.set)
              
            if self.include_horizontal_scrollbar: 
                self.scrollbar_x = ttk.Scrollbar(self, 
                    orient=u'horizontal', command=self.text.xview)
                self.scrollbar_x.grid(row=1, column=0, sticky=u'nsew') 
    #             self.scrollbar_y_logfile.pack(fill='x', expand=True)
                self.text.configure(xscrollcommand=self.scrollbar_x.set)
        
            grid_configure(self, rows={0:50}, columns={0:100})
        
        self.text.config(state=self.state)
            
    #===========================================================================
    def add_text(self, string):
        self.text.config(state=u'normal')
        current_text = self.text.get('1.0','end')
        if current_text.strip():
            self.text.insert('end', u'\n' + string) 
        else:
            self.text.insert('end', string)
        self.text.config(state=self.state) 
        self.text.see('end')
        
    #===========================================================================
    def clear_all(self):
        self.text.config(state=u'normal')
        self.text.delete('1.0', u'end') 
        self.text.config(state=self.state)
        
    #===========================================================================
    def get_text(self):
        return self.text.get('1.0','end')


class TimeWidgetSeason(tk.Frame):
    """
    Widget to select month and day to represent a season.
    """

    def __init__(self,
                 parent=False,
                 prop_frame={},
                 prop_combobox={},
                 grid_items={},
                 callback_target=None,
                 **kwargs):

        self.parent = parent

        self.callback_target = callback_target

        self.prop_frame = {}
        self.prop_frame.update(prop_frame)

        self.prop_combobox = {'width': 8,
                              'state': 'readonly'}
        self.prop_combobox.update(prop_combobox)

        self.grid_frame = {'sticky': 'nsew'}
        self.grid_frame.update(kwargs)

        self.grid_items = {'sticky': 'w',
                           'padx': 5,
                           'pady': 2}
        self.grid_items.update(grid_items)

        # Create frame
        tk.Frame.__init__(self, parent, **self.prop_frame)
        self.grid(**self.grid_frame)

        self.month_list = ['January', 'February', 'Mars', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December']
        self.day_list = list(map(str, range(1, 32)))

        self.name_to_num = {}
        self.num_to_name = {}
        for nr, name in enumerate(self.month_list):
            self.name_to_num[name] = nr+1
            self.num_to_name[nr+1] = name

        self._set_frame()

    # ===========================================================================
    def _set_frame(self):

        self.combobox = {}

        prop_month = {'width': 25}
        prop_day = {'width': 5}

        # From
        tk.Label(self, text='From:').grid(row=0, column=0, **self.grid_items)
        self.combobox['month_from'] = ComboboxWidget(self, items=self.month_list, prop_combobox=prop_month, row=0, column=1)
        self.combobox['day_from'] = ComboboxWidget(self, items=self.day_list, prop_combobox=prop_day, row=0, column=2)

        # To
        tk.Label(self, text='To:').grid(row=1, column=0, **self.grid_items)
        self.combobox['month_to'] = ComboboxWidget(self, items=self.month_list, prop_combobox=prop_month, row=1, column=1)
        self.combobox['day_to'] = ComboboxWidget(self, items=self.day_list, prop_combobox=prop_day, row=1, column=2)

        grid_configure(self, nr_rows=2, nr_columns=3)

    def get_value(self):
        return_dict = {}
        for key, combobox in self.combobox.items():
            value = combobox.get_value()
            return_dict[key] = int(self.name_to_num.get(value, value))
        return return_dict

    def set_value(self, **kwargs):
        for key, value in kwargs.items():
            if key in self.combobox:
                if 'month' in key:
                    self.combobox[key].set_value(self.num_to_name.get(value, value))
                else:
                    self.combobox[key].set_value(str(value))

    def reset_widget(self):
        self.combobox['month_from'].set_value(self.month_list[0])
        self.combobox['month_to'].set_value(self.month_list[-1])
        self.combobox['day_from'].set_value('1')
        self.combobox['day_to'].set_value('31')


class TimeWidgetMonthSelector(ttk.LabelFrame):
    """
    Widget to select month and year.
    """
    def __init__(self,
                 parent=False,
                 title='',
                 prop_frame={},
                 grid_items={},
                 callback_target=None,
                 **kwargs):

        self.parent = parent

        self.callback_target = callback_target

        self.prop_frame = {'text': title}
        self.prop_frame.update(prop_frame)


        self.grid_frame = {'sticky': 'nsew'}
        self.grid_frame.update(kwargs)

        self.grid_items = {'sticky': 'w',
                           'padx': 5,
                           'pady': 2}
        self.grid_items.update(grid_items)

        # Create frame
        ttk.LabelFrame.__init__(self, parent, **self.prop_frame)
        self.grid(**self.grid_frame)

        # self.year_list = list(range(1990, datetime.datetime.now().year))
        self.month_list = ['January', 'February', 'Mars', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December']

        self.name_to_num = {}
        self.num_to_name = {}
        for nr, name in enumerate(self.month_list):
            self.name_to_num[name] = nr+1
            self.num_to_name[nr+1] = name

        self.year = datetime.datetime.now().year
        self.month = datetime.datetime.now().month

        self._set_frame()
        self.set()

    # ===========================================================================
    def _set_frame(self):

        self.string_length = 14
        self.stringvar_year_month = tk.StringVar()
        self.stringvar_year_month.set(' '*self.string_length)

        self.button_back = tk.Button(self, text='<<', command=self._back)
        self.button_back.grid(row=0, column=0, sticky='w')

        self.label_year_month = tk.Label(self, textvariable=self.stringvar_year_month, font="Consolas\ Sans 9", width=self.string_length)
        self.label_year_month.grid(row=0, column=1, sticky='ew')

        self.button_forward = tk.Button(self, text='>>', command=self._forward)
        self.button_forward.grid(row=0, column=2, sticky='e')

        grid_configure(self, nr_rows=1, nr_columns=3)

    def set(self, year=None, month=None, callback=False):
        if not year:
            year = self.year
        if not month:
            month = self.month

        year_month_str = '{} {}'.format(year, self._get_month_str(month))
        year_month_str = year_month_str.rjust(self.string_length, ' ')
        self.stringvar_year_month.set(year_month_str)

        if callback and self.callback_target:
            self.callback_target()

    def get(self):
        year_month_string = self.stringvar_year_month.get().strip()
        year, month = year_month_string.split(' ')
        return int(year), int(self._get_month_num(month))

    def _back(self):
        year, month = self.get()
        if month == 1:
            month = 12
            year -= 1
        else:
            month -= 1
        self.set(year=year, month=month, callback=True)

    def _forward(self):
        year, month = self.get()

        if month == 12:
            month = 1
            year += 1
        else:
            month += 1
        self.set(year=year, month=month, callback=True)

    def _get_month_str(self, month):
        return self.num_to_name.get(month, month)

    def _get_month_num(self, month):
        return self.name_to_num.get(month, month)

    def disable_widget(self):
        disable_widgets(self.button_back, self.button_forward)

    def enable_widget(self):
        enable_widgets(self.button_back, self.button_forward)


class TimeWidget(tk.LabelFrame):
    """
    Updated 20180825    
    """
    def __init__(self, 
                 parent=False, 
                 title='', 
                 lowest_time_resolution='minute', 
                 show_header=True, 
                 prop_frame={}, 
                 prop_combobox={}, 
                 grid_items={}, 
                 callback_target=None, 
                 **kwargs):
        
        self.parent = parent
        self.show_header = show_header
        
        self.lowest_time_resolution = lowest_time_resolution
        time_res = ['year', 'month','day', 'hour', 'minute', 'second']
        self.time_resolution = []
        for tr in time_res:
            self.time_resolution.append(tr)
            if tr == lowest_time_resolution:
                break

        self.callback_target = callback_target

        self.from_time = None
        self.to_time = None
        
        self.prop_frame = {}
        self.prop_frame.update(prop_frame)
        if title:
            self.prop_frame.update({'text': title})
        
        self.prop_combobox = {'width':8, 
                              'state':'readonly'}
        self.prop_combobox.update(prop_combobox)
        
        self.grid_frame = {'sticky': 'nsew'}
        self.grid_frame.update(kwargs) 
        
        self.grid_items = {'sticky': 'w', 
                           'padx': 5, 
                           'pady': 2}
        self.grid_items.update(grid_items)
        
        # Create frame
        ttk.LabelFrame.__init__(self, parent, **self.prop_frame)
        self.grid(**self.grid_frame)
        
        self._initiate_attributes()
        self._set_frame()
       
        
    #===========================================================================
    def _initiate_attributes(self):
        
        self.combobox = dict((part, None) for part in self.time_resolution)
        self.stringvar = dict((part, tk.StringVar()) for part in self.time_resolution)
        self.time_lists = dict((part, []) for part in self.time_resolution)
       
        self.time_formats = ['%Y%m%d', 
                             '%Y%m%d%H', 
                             '%Y%m%d%H%M', 
                             '%Y%m%d%H%M%S', 
                             '%Y-%m-%d', 
                             '%Y-%m-%d %H', 
                             '%Y-%m-%d %H:%M', 
                             '%Y-%m-%d %H%:M:%S']
            

    #===========================================================================
    def _set_frame(self):
        r=0        
        if self.show_header:
            for c, part in enumerate(self.time_resolution):
                tk.Label(self, text=part.capitalize()).grid(row=r, column=c, **self.grid_items)
            r+=1
#         print(r
        for c, part in enumerate(self.time_resolution):
            self.combobox[part] = ttk.Combobox(self, 
                                                textvariable=self.stringvar[part], 
                                                **self.prop_combobox)
            self.combobox[part].grid(row=r, column=c, **self.grid_items)
            self.combobox[part].bind('<<ComboboxSelected>>', self._on_select)
#        r+=1
#         print(r
        
        grid_configure(self, nr_rows=2, nr_columns=5)
    
    
    #===========================================================================
    def _on_select(self, event=None):
        # Save time
        time_list = []
        for part in self.time_resolution:
            v = self.stringvar[part].get().lstrip('0')
            if not v:
                v = '0'
            time_list.append(v)
            
        eval_string = 'datetime.datetime(%s)' % ', '.join(time_list)
        
        self.current_time = eval(eval_string)
        self.current_datenumber = dates.date2num(self.current_time)
        
        if self.callback_target:
            self.callback_target()
    
    
    #===========================================================================
    def _get_padded_string_list(self, items, nr):
        return [str(item).rjust(nr, '0') for item in items]
        
        
    #===========================================================================
    def set_valid_time_span_from_list(self, time_list):
        self.set_valid_time_span(min(time_list), max(time_list))
        
        
    #===========================================================================
    def set_valid_time_span(self, from_time, to_time):
        if type(from_time) == str:
            for time_format in self.time_formats:
                try:
                    from_time = datetime.datetime.strptime(from_time, time_format)
                    to_time = datetime.datetime.strptime(to_time, time_format)
                except:
                    pass
        else:
            from_time = pd.to_datetime(from_time)
            to_time = pd.to_datetime(to_time)

        self.from_time = from_time
        self.to_time = to_time
        
        from_year = from_time.year
        from_month = from_time.month
        from_day = from_time.day
        from_hour = from_time.hour
        
        to_year = to_time.year    
        to_month = to_time.month
        to_day = to_time.day
        to_hour = to_time.hour

        for part in self.time_resolution:
            if part == 'year':
                self.time_lists[part] = map(str, range(from_year, to_year+1))
            
            elif part == 'month':
                if from_year == to_year:
                    self.time_lists[part] = map(str, range(from_month, to_month+1))
                else:
                    self.time_lists[part] = self._get_padded_string_list(range(1, 13), 2)
            elif part == 'day':
                if from_year == to_year and from_month == to_month: 
                    self.time_lists[part] = self._get_padded_string_list(range(from_day, to_day+1), 2)
                else:
                    self.time_lists[part] = self._get_padded_string_list(range(1, 31), 2)
            elif part == 'hour':
                if from_year == to_year and from_month == to_month and from_day == to_day: 
                    self.time_lists[part] = self._get_padded_string_list(range(from_hour, to_hour+1), 2)
                else:
                    self.time_lists[part] = self._get_padded_string_list(range(1, 24), 2)
            elif part == 'minute':
                self.time_lists[part] = self._get_padded_string_list(range(60), 2)
            
            elif part == 'second':
                self.time_lists[part] = self._get_padded_string_list(range(60), 2)
                
            self.combobox[part]['values'] = tuple(self.time_lists[part])
#             print(self.combobox[part]['values']
#             print('='*30
#             self.combobox[part]['width'] = 15
            self.combobox[part].update_idletasks()
#            
            
    #===========================================================================
    def set_time(self, time_string=None, datenumber=None, datetime_object=None, first=False, last=False):
        
        time_object = None
        if datetime_object:
            time_object = datetime_object
        elif time_string:
            for time_format in self.time_formats:
                try:
                    time_object = datetime.datetime.strptime(time_string, time_format)
                    # print('time_object'.upper(), time_object)
                    self.current_datenumber = dates.date2num(time_object)
                except:
                    pass
        elif datenumber:
            self.current_datenumber = datenumber
            time_object = dates.num2date(datenumber)
        elif first:
            # print('FIRST', time_object)
            time_object = self.from_time
        elif last:
            # print('LAST', time_object)
            time_object = self.to_time
        
        if not time_object:
            return
        self.current_time = time_object
        
        year, month, day, hour, minute, second = self.current_time.strftime('%Y %m %d %H %M %S').split()
        
        for part in self.time_resolution:
            string = eval(part)
            self.stringvar[part].set(string)
            
    #===========================================================================
    def get_time_object(self):
        time_string = ''
        for part in self.time_resolution:
            if not time_string:
                time_string = self.stringvar[part].get()
            else:
                time_string = time_string + ', ' + str(int(self.stringvar[part].get()))
        if not time_string:
            return None
        datetime_object = datetime.datetime(*eval(time_string))
        return datetime_object

    def get_time_string(self, string_format='%Y%m%d%H%M%S'):
        time_object = self.get_time_object()
        if not time_object:
            return None
        return time_object.strftime(string_format)

    #===========================================================================
    def get_time_number(self):
        datetime_object = self.get_time_object()
        date_number = dates.date2num(datetime_object)
#        print('date_number'.upper(), date_number
        return date_number
        
    #===========================================================================
    def reset_widget(self):
        # Remove values and current value in comboboxes
        for part in self.time_resolution:
            self.combobox[part]['values'] = []
            self.stringvar[part].set('')

    def clear_widget(self):
        """
        Clears selection (sets all entries to "blanc")
        :return:
        """
        for part in self.time_resolution:
            self.stringvar[part].set('')

    def disable_widget(self):
        disable_widgets(*self.combobox.values())

    def enable_widget(self):
        enable_widgets(*self.combobox.values())
"""
================================================================================
================================================================================
================================================================================
"""
class FlagWidget(tk.Frame): 
    
    #===========================================================================
    class Selection():
        #===========================================================================
        def __init__(self):
            self.flag = None
            self.selected_descriptions = []
            self.selected_flags = []
            self.colors = {}
            self.markersize = {}
            self.edge = True
            
        def get_prop(self, flag, markeredgecolor='black'):
            prop = {}
            if flag in self.colors:
                prop.update({'color': self.colors[flag]}) 
                
            if flag in self.markersize:
                prop.update({'markersize': self.markersize[flag]})
                
            if self.edge:
                prop.update({'markeredgecolor': self.colors[flag]})
            else:
                prop.update({'markeredgecolor': markeredgecolor})
                
            return prop
    
    
    #===========================================================================
    def __init__(self, 
                 parent, 
                 flags=[], 
                 descriptions=[], 
                 colors=[], 
                 markersize=[], 
                 default_colors=[], 
                 prop_frame={}, 
                 default_flag='', 
                 include_flagging=True, 
                 include_marker_size=False, 
                 include_color_selection=True, 
                 ignore_color=False,
                 edge_checkbutton=False, 
                 callback_flag_data=None, 
                 callback_update=None, 
                 callback_prop_change=None,
                 text='',
                 **kwargs):
        
        self.flags = flags
        if '' in self.flags:
            self.flags[self.flags.index('')] = 'no flag'
        self.descriptions = descriptions
        self.include_flagging = include_flagging
        self.include_marker_size = include_marker_size
        self.include_color_selection = include_color_selection
        self.ignore_color = ignore_color
        self.default_colors = default_colors
        self.colors = colors
        self.markersize = markersize
        self.text = text
        
        if not self.colors:
            self.colors = ['blue', 'red', 'darkgreen', 'yellow', 'magenta', 'cyan', 'black', 'gray']
            for c in self.default_colors:
                if c not in self.colors:
                    self.colors.append(c)
            self.colors = sorted(self.colors)
            
        if not self.default_colors:
            self.default_colors = self.colors[:]
            
        if not self.markersize:
            self.markersize = [2]*len(self.flags)
        
        self.default_flag = default_flag
        if not default_flag or default_flag not in self.flags:
            self.default_flag = self.flags[0]
            
        self.edge_checkbutton = edge_checkbutton
        
        self.callback_flag_data = callback_flag_data
        self.callback_update = callback_update
        self.callback_prop_change = callback_prop_change
        
        self.selection = self.Selection()
        
        self.radiobutton_widget_flags = None
        self.checkbutton_widget_flags = None
        
        self.prop_frame = {}
        self.prop_frame.update(prop_frame)
        
        self.grid_frame = {'padx': 5, 
                           'pady': 5, 
                           'sticky': 'nsew'}
        self.grid_frame.update(kwargs)
        
        tk.Frame.__init__(self, parent, **self.prop_frame)
        self.grid(**self.grid_frame)
            
        self._set_frame()
        
        
    #===========================================================================
    def _set_frame(self):
        padx = 5
        pady = 5

        rr = 0
        if self.text:
            text_frame = tk.Frame(self)
            text_frame.grid(row=rr, column=0, padx=padx, pady=pady, sticky='w')
            self.text_widget = tk.Text(text_frame, wrap=tk.WORD, height=5, bg='lightgray')
            self.text_widget.grid(row=0, column=0, padx=padx, pady=pady, sticky='w')
            self.text_widget.insert('end', self.text)
            grid_configure(text_frame)
            self.text_widget.config(state='disabled')
            # self.label_text = WrappedLabel(text_frame, text=self.text)
            rr+=1
        
        frame = tk.Frame(self)
        frame.grid(row=rr, column=0, padx=padx, pady=pady, sticky='w')
        grid_configure(self, nr_rows=rr+1)
        
        r=0
        c=0
        
#        nr_rows = 0
        
        self.stringvar_color = {}
        self.stringvar_marker_size = {}

        if self.include_flagging:
            # Radiobutton to select which flag to use
            color_dict = {flag: col for flag, col in zip(self.flags, self.default_colors)}
            self.radiobutton_widget_flags = RadiobuttonWidget(frame, 
                                                              column=c, 
                                                              row=r, 
                                                              items=self.flags, 
                                                              default_item=self.default_flag, 
                                                              colors=color_dict)
            
            c+=1
        
        if self.descriptions:
            if self.ignore_color:
                color_dict = {}
            else:
                color_dict = {flag: col for flag, col in zip(self.descriptions, self.default_colors)}
            self.checkbutton_widget_flags = CheckbuttonWidget(frame, 
                                                              items=self.descriptions, 
                                                              pre_checked_items=self.descriptions, 
                                                              include_select_all=False, 
                                                              colors=color_dict,
                                                              pady=0, 
                                                              row=r, 
                                                              column=c)
            c+=1

        if self.include_color_selection:
            # Color selection
            color_frame = tk.Frame(frame)
            color_frame.grid(row=r, column=c)
            width = 12
            row=0
            
            self.combobox_color = {}
            for k, flag_nr in enumerate(self.flags):
                self.stringvar_color[flag_nr] = tk.StringVar()
                self.combobox_color[flag_nr] = ttk.Combobox(color_frame, 
                                                   width=width, 
                                                   state='readonly', 
                                                   textvariable=self.stringvar_color[flag_nr])
                self.combobox_color[flag_nr].grid(row=row, column=c, sticky='w', padx=padx, pady=2)
                self.combobox_color[flag_nr]['values'] = sorted(self.colors)
                self.stringvar_color[flag_nr].set(self.default_colors[k])
                self.combobox_color[flag_nr].config(foreground=self.default_colors[k])
                self.combobox_color[flag_nr].bind('<<ComboboxSelected>>', lambda event, flag_nr=flag_nr: self._on_change_flag_color(flag_nr)) 
                row+=1
#                if r > nr_rows:
#                    nr_rows = r
            
            grid_configure(color_frame)
            c+=1
        
        if self.include_marker_size:
            # Symbol size selection
            size_frame = tk.Frame(frame)
            size_frame.grid(row=r, column=c)
            width = 3
            row=0
            self.combobox_marker_size = {}
            for k, flag_nr in enumerate(self.flags):
                self.stringvar_marker_size[flag_nr] = tk.StringVar()
                self.combobox_marker_size[flag_nr] = ttk.Combobox(size_frame, 
                                                   width=width, 
                                                   state='readonly', 
                                                   textvariable=self.stringvar_marker_size[flag_nr])
                self.combobox_marker_size[flag_nr].grid(row=row , column=c, sticky='w', padx=padx, pady=2)
                self.combobox_marker_size[flag_nr]['values'] = list(map(str, range(1, 12)))
                self.stringvar_marker_size[flag_nr].set(str(self.markersize[k]))
                self.combobox_marker_size[flag_nr].config(foreground=self.default_colors[k])
                self.combobox_marker_size[flag_nr].bind('<<ComboboxSelected>>', self._on_change)
#                 self.combobox_marker_size[flag_nr].bind('<<ComboboxSelected>>', lambda event, flag_nr=flag_nr: self._on_change_marker_size(flag_nr)) 
                row+=1
            grid_configure(size_frame)
            r+=1
        
        r+=1
        c=0
        # Buttons
        if self.include_flagging:
            self.button_flag = ttk.Button(frame, text='Flag selected data', command=self._on_buttonpress_flag)
            self.button_flag.grid(row=r, column=c, columnspan=1, padx=padx, pady=pady, sticky='w')
            c+=1
        
        self.button_update_flags = ttk.Button(frame, text='Update flags to show', command=self._on_buttonpress_update)
        self.button_update_flags.grid(row=r, column=c, columnspan=1, padx=padx, pady=pady, sticky='w')
        
        c+=1
        
        if self.edge_checkbutton:
            # Edge option
            self.booleanvar_edge = tk.BooleanVar()
            self.cbutton_edge = tk.Checkbutton(frame, 
                                              text='Edge',  
                                              variable=self.booleanvar_edge, 
                                              command=self.get_selection)
            self.cbutton_edge.grid(row=r, column=c, sticky='w', padx=padx, pady=2)
            self.booleanvar_edge.set(False)
            r+=1
        
        # grid_configure(frame, nr_rows=len(self.flags)+1, nr_columns=4)
        grid_configure(frame, nr_rows=r+1, nr_columns=4)
        
        
    #===========================================================================
    def _on_change_flag_color(self, flag_nr): 
        i = self.flags.index(flag_nr)
        new_color = self.stringvar_color[flag_nr].get()
        if new_color:
            if self.radiobutton_widget_flags:
                self.radiobutton_widget_flags.change_color(flag_nr, new_color)
            if self.checkbutton_widget_flags:
                self.checkbutton_widget_flags.change_color(self.descriptions[i], new_color)
            self.combobox_color[flag_nr].config(foreground=new_color)
            if self.include_marker_size:
                self.combobox_marker_size[flag_nr].config(foreground=new_color)            
            self._on_change()
        
    #===========================================================================
    def _on_buttonpress_flag(self):
        self.get_selection()
        if self.callback_flag_data: 
            self.callback_flag_data()
    
    #===========================================================================
    def _on_buttonpress_update(self):
        self.get_selection()
        if self.callback_update: 
            self.callback_update()
            
    #===========================================================================
    def _on_change(self, event=None):
        self.get_selection()
        if self.callback_prop_change: 
            self.callback_prop_change()
    
    #===========================================================================
    def get_selection(self):
        
        if self.radiobutton_widget_flags:
            self.selection.flag = self.radiobutton_widget_flags.get()
            if self.selection.flag == 'no flag':
                self.selection.flag = ''
        
        if self.checkbutton_widget_flags:
            self.selection.selected_descriptions = self.checkbutton_widget_flags.get_checked_item_list()
            self.selection.selected_flags = [flag for flag, des in zip(self.flags, self.descriptions) if des in self.selection.selected_descriptions]
        
        if self.ignore_color:
            self.selection.colors = {}
        else:
            self.selection.colors = dict(zip(self.flags, [self.stringvar_color[k].get() for k in self.flags]))
        
        if self.include_marker_size:
            self.selection.markersize = dict(zip(self.flags, [int(self.stringvar_marker_size[k].get()) for k in self.flags]))
        
        if self.edge_checkbutton:
            self.selection.edge = self.booleanvar_edge.get()
        
        
        return self.selection


class DirectoryWidget(tk.Frame):

    def __init__(self,
                 parent,
                 prop_frame={},
                 prop_entry={},
                 default_directory='',
                 include_default_button=True,
                 callback=None,
                 **kwargs):
        self.prop_frame = {}
        self.prop_frame.update(prop_frame)

        self.prop_entry = {'width': 50}
        self.prop_entry.update(prop_entry)

        self.grid_frame = {'padx': 5,
                           'pady': 5,
                           'sticky': 'nsew'}
        self.grid_frame.update(kwargs)

        tk.Frame.__init__(self, parent, **self.prop_frame)
        self.grid(**self.grid_frame)

        self.callback = callback
        self.default_directory = default_directory
        self.include_default_button = include_default_button

        self._set_frame()


    # ===========================================================================
    def _set_frame(self):
        padx = 5
        pady = 5

        frame = tk.Frame(self)
        frame.grid(row=0, column=0, padx=padx, pady=pady, sticky='w')
        grid_configure(self)

        r = 0
        c = 0

        # tk.Label(frame, text='Directory:').grid(row=r, column=c, padx=padx, pady=pady, sticky='nw')
        self.stringvar_directory = tk.StringVar()
        self.entry_directory = tk.Entry(frame, textvariable=self.stringvar_directory, **self.prop_entry)
        self.entry_directory.grid(row=0, column=0, columnspan=2, padx=padx, pady=pady, sticky='nw')
        self.stringvar_directory.trace("w",
                                       lambda name, index, mode, sv=self.stringvar_directory: check_path_entry(sv))

        ttk.Button(frame, text='Get directory', command=self._get_directory).grid(row=1,
                                                                                  column=0,
                                                                                  padx=padx,
                                                                                  pady=pady, sticky='se')

        if self.include_default_button:
            ttk.Button(frame, text='Default directory', command=self.set_default_directory).grid(row=1,
                                                                                                 column=1,
                                                                                                 padx=padx,
                                                                                                 pady=pady,
                                                                                                 sticky='se')

        grid_configure(frame, nr_rows=2, nr_columns=2)

    def _get_directory(self):
        directory = tk.filedialog.askdirectory()
        if directory:
            self.set_directory(directory)

    def set_default_directory(self):
        if self.default_directory:
            self.set_directory(self.default_directory)

    def get_directory(self):
        return self.stringvar_directory.get()

    def set_directory(self, directory, call_target=True):
        self.stringvar_directory.set(directory)
        if self.callback and call_target:
            self.callback()

    def get_value(self):
        return self.stringvar_directory.get()

    def set_value(self, directory):
        self.set_directory(directory)


class FilePathWidget(tk.Frame):

    def __init__(self,
                 parent,
                 prop_frame={},
                 prop_entry={},
                 default_directory='',
                 callback=None,
                 **kwargs):
        self.prop_frame = {}
        self.prop_frame.update(prop_frame)

        self.prop_entry = {'width': 50}
        self.prop_entry.update(prop_entry)

        self.grid_frame = {'padx': 5,
                           'pady': 5,
                           'sticky': 'nsew'}
        self.grid_frame.update(kwargs)

        tk.Frame.__init__(self, parent, **self.prop_frame)
        self.grid(**self.grid_frame)

        self.callback = callback
        self.default_directory = default_directory

        self._set_frame()


    # ===========================================================================
    def _set_frame(self):
        padx = 5
        pady = 5

        frame = tk.Frame(self)
        frame.grid(row=0, column=0, padx=padx, pady=pady, sticky='w')
        grid_configure(self)

        r = 0
        c = 0

        # tk.Label(frame, text='Directory:').grid(row=r, column=c, padx=padx, pady=pady, sticky='nw')
        self.stringvar_path = tk.StringVar()
        self.entry_path = tk.Entry(frame, textvariable=self.stringvar_path, **self.prop_entry)
        self.entry_path.grid(row=0, column=0, columnspan=2, padx=padx, pady=pady, sticky='nw')
        self.stringvar_path.trace("w",
                                       lambda name, index, mode, sv=self.stringvar_path: check_path_entry(sv))

        ttk.Button(frame, text='Get file', command=self._get_file_path).grid(row=1,
                                                                                  column=0,
                                                                                  padx=padx,
                                                                                  pady=pady, sticky='se')

        grid_configure(frame, nr_rows=2, nr_columns=2)

    def _get_file_path(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename()
        if path:
            self.set_path(path)

    def get_path(self):
        return self.stringvar_path.get()

    def set_path(self, path, call_target=True):
        self.stringvar_path.set(path)
        if self.callback and call_target:
            self.callback()

    def get_value(self):
        return self.stringvar_path.get()

    def set_value(self, directory):
        self.set_path(directory)


class DirectoryWidgetLabelframe(ttk.LabelFrame):

    def __init__(self,
                 parent,
                 label='Directory',
                 prop_frame={},
                 prop_entry={},
                 default_directory='',
                 include_default_button=True,
                 callback=None,
                 **kwargs):
        self.prop_frame = {}
        self.prop_frame.update(prop_frame)

        self.prop_entry = {'width': 50}
        self.prop_entry.update(prop_entry)

        self.grid_frame = {'padx': 5,
                           'pady': 5,
                           'sticky': 'nsew'}
        self.grid_frame.update(kwargs)

        ttk.LabelFrame.__init__(self, parent, text=label, **self.prop_frame)
        self.grid(**self.grid_frame)

        self.callback = callback
        self.default_directory = default_directory
        self.include_default_button = include_default_button

        self._set_frame()


    # ===========================================================================
    def _set_frame(self):
        padx = 5
        pady = 5

        frame = tk.Frame(self)
        frame.grid(row=0, column=0, padx=padx, pady=pady, sticky='w')
        grid_configure(self)

        r = 0
        c = 0

        # tk.Label(frame, text='Directory:').grid(row=r, column=c, padx=padx, pady=pady, sticky='nw')
        self.stringvar_directory = tk.StringVar()
        self.entry_directory = tk.Entry(frame, textvariable=self.stringvar_directory, **self.prop_entry)
        self.entry_directory.grid(row=0, column=0, columnspan=2, padx=padx, pady=pady, sticky='nw')
        self.stringvar_directory.trace("w",
                                       lambda name, index, mode, sv=self.stringvar_directory: check_path_entry(sv))

        ttk.Button(frame, text='Get directory', command=self._get_directory).grid(row=1, column=0,
                                                                                  padx=padx,
                                                                                  pady=pady, sticky='se')

        if self.include_default_button and self.default_directory:
            ttk.Button(frame, text='Default directory', command=self.set_default_directory).grid(row=1, column=1,
                                                                                      padx=padx,
                                                                                      pady=pady, sticky='se')


        grid_configure(frame, nr_rows=2, nr_columns=2)

    def _get_directory(self):
        directory = tk.filedialog.askdirectory()
        if directory:
            self.set_directory(directory)

    def set_default_directory(self):
        if self.default_directory:
            self.set_directory(self.default_directory)


    def get_directory(self):
        return self.stringvar_directory.get()

    def set_directory(self, directory, call_target=True):
        self.stringvar_directory.set(directory)
        if self.callback and call_target:
            self.callback()

    def get_value(self):
        return self.stringvar_directory.get()

    def set_value(self, directory):
        self.set_directory(directory)


class WrappedLabel(tk.Label):
    def __init__(self,
                 parent,
                 text='',
                 prop_frame={},
                 prop_label={},
                 callback=None,
                 user=None,
                 **kwargs):

        self.frame = tk.Frame(parent)
        self.frame.grid(row=0, column=0, sticky='nsew')
        grid_configure(self.frame)

        self.prop_label = {}
        self.prop_label.update(prop_label)

        self.grid_frame = {'padx': 5,
                           'pady': 5,
                           'sticky': 'nsew'}
        self.grid_frame.update(kwargs)

        tk.Label.__init__(self, parent, text=text, **self.prop_label)
        self.grid(**self.grid_frame)

        self.bind('<Configure>', self._update_wrap)

    def _update_wrap(self, event):
        self.config(wraplength=self.frame.winfo_width())


class TableWidget(tk.Frame):
    """
    Table based on ttk.TreeView widget.
    Sorting functionality etc. taken from:
    https://stackoverflow.com/questions/32051780/how-to-edit-the-style-of-a-heading-in-treeview-python-ttk
    """
    def __init__(self,
                 parent=False,
                 prop_frame={},
                 prop_treeview={},
                 columns=[],
                 int_columns=[],
                 callback_select=[],
                 callback_rightclick=None,
                 **kwargs):

        self.parent = parent

        self.callback_select_targets = []
        if not isinstance(callback_select, list):
            self.callback_select_targets = [callback_select]
        else:
            self.callback_select_targets = callback_select

        self.callback_rightclick = callback_rightclick

        self.prop_frame = {}
        self.prop_frame.update(prop_frame)

        self.prop_treeview = {'selectmode': 'browse'}
        self.prop_treeview.update(prop_treeview)

        self.grid_frame = {'padx': 5,
                           'pady': 5,
                           'sticky': 'nsew'}
        self.grid_frame.update(kwargs)

        # Create frame
        tk.Frame.__init__(self, parent, **self.prop_frame)
        self.grid(**self.grid_frame)

        self.columns = columns[:]
        self.int_columns = int_columns

        self._set_frame()

    def _set_frame(self):
        self.tree = ttk.Treeview(self, columns=self.columns, show="headings", **self.prop_treeview)

        #self.xscrollbar = ttk.Scrollbar(self, orient='horizontal', command=self.tree.xview)
        self.yscrollbar = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)

        #self.tree.configure(xscrollcommand=self.xscrollbar.set)
        self.tree.configure(yscrollcommand=self.yscrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        #self.xscrollbar.grid(row=1, column=0, sticky='sew')
        self.yscrollbar.grid(row=0, column=1, sticky='nsw')

        #self.xscrollbar.configure(command=self.tree.xview)
        self.yscrollbar.configure(command=self.tree.yview)

        self.tree.config(**self.prop_treeview)

        grid_configure(self, nr_rows=1, nr_columns=2, c0=20)

        # Bindings
        self.tree.bind('<<TreeviewSelect>>', self._callback_select)

        if self.callback_rightclick:
            MenuWidget(self.tree, bind_widget=self.tree, items=[{'name': 'Show filter', 'command': self.callback_rightclick}])

    def _callback_select(self, event=None):
        for callback in self.callback_select_targets:
            callback(**self.get_selected())

    def get_selected(self):
        selection = self.tree.selection()
        item_dict = self.tree.item(selection)
        return_dict = {col: value for col, value in zip(self.columns, item_dict['values'])}
        return return_dict

    def get_filtered_items(self):
        children = self.tree.get_children('')
        return_list = []
        for c in children:
            item_dict = self.tree.item(c)
            c_dict = {col: value for col, value in zip(self.columns, item_dict['values'])}
            return_list.append(c_dict)
        return return_list

    def reset_table(self):
        """
        Deletes all items in the treeview.
        :return:
        """
        for i in self.tree.get_children():
            self.tree.delete(i)

    def set_table(self, data_rows):
        """
        Sets the treeview widget with data from the data_rows. Structure is:

        :param data_rows_rows:
        :return:
        """
        # for col in self.columns:
        #     self.tree.heading(col, text=col.title(), command=lambda c=col: sortby(self.tree, c, 0))

        for col in self.columns:
            if col in self.int_columns:
                self.tree.heading(col, text=col,
                                  command=lambda c=col: sortby_int(self.tree, c, False))
            else:
                self.tree.heading(col, text=col,
                                  command=lambda c=col: sortby(self.tree, c, False))
        for item in data_rows:
            self.tree.insert('', 'end', values=item, tags=('items',))

        def sortby(tree, col, descending):
            """sort tree contents when a column header is clicked on"""
            # grab values to sort
            data = [(tree.set(child, col), child) for child in tree.get_children('')]
            # if the data to be sorted is numeric change to float
            # data =  change_numeric(data)
            # now sort the data in place
            data.sort(reverse=descending)
            for ix, item in enumerate(data):
                tree.move(item[1], '', ix)
            # switch the heading so it will sort in the opposite direction
            tree.heading(col, command=lambda col=col: sortby(tree, col, int(not descending)))


        def sortby_int(tv, col, reverse):
            """
            https://stackoverflow.com/questions/22032152/python-ttk-treeview-sort-numbers
            :param tv:
            :param col:
            :param reverse:
            :return:
            """
            l = [(tv.set(k, col), k) for k in tv.get_children('')]
            l.sort(key=lambda t: int(t[0]), reverse=reverse)
            #      ^^^^^^^^^^^^^^^^^^^^^^^

            for index, (val, k) in enumerate(l):
                tv.move(k, '', index)

            tv.heading(col,
                       command=lambda: sortby_int(tv, col, not reverse))

        # root = Tk()
        # columns = ('number',)
        # treeview = ttk.Treeview(root, columns=columns, show='headings')
        # for t in ('1', '10', '11', '2', '3'):
        #     treeview.insert('', END, values=(t,))
        # treeview.pack()
        # for col in columns:
        #     treeview.heading(col, text=col,
        #                      command=lambda c=col: treeview_sort_column(treeview, c, False))


class TreeviewWidget(tk.Frame):
    """

    """
    def __init__(self,
                 parent=False,
                 prop_frame={},
                 prop_treeview={},
                 columns=[],
                 int_columns=[],
                 callback_target=[],
                 **kwargs):

        self.parent = parent

        if not isinstance(callback_target, list):
            self.callback_targets = [callback_target]
        else:
            self.callback_targets = callback_target

        self.prop_frame = {}
        self.prop_frame.update(prop_frame)

        self.prop_treeview = {}
        # self.prop_treeview = {'height': 5}
        # self.prop_treeview.update(prop_treeview)

        self.grid_frame = {'padx': 5,
                           'pady': 5,
                           'sticky': 'nsew'}
        self.grid_frame.update(kwargs)

        # Create frame
        tk.Frame.__init__(self, parent, **self.prop_frame)
        self.grid(**self.grid_frame)

        self.columns = columns
        self.int_columns = int_columns

        self._set_frame()

    def _set_frame(self):

        self.tree = ttk.Treeview(self)

        self.xscrollbar = ttk.Scrollbar(self, orient='horizontal', command=self.tree.xview)
        self.yscrollbar = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)

        self.tree.configure(xscrollcommand=self.xscrollbar.set)
        self.tree.configure(yscrollcommand=self.yscrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.xscrollbar.grid(row=1, column=0, sticky='sew')
        self.yscrollbar.grid(row=0, column=1, sticky='nse')

        self.xscrollbar.configure(command=self.tree.xview)
        self.yscrollbar.configure(command=self.tree.yview)

        if len(self.columns) > 1:
            self.prop_treeview.update({'columns': self.columns[1:]})

        self.tree.config(**self.prop_treeview)

        for k, value in enumerate(self.columns):
            item = '#{}'.format(k)
            self.tree.heading(item, text=value)

        grid_configure(self)

        # Bindings
        self.tree.bind('<<TreeviewSelect>>', self._callback_select)

    def _callback_select(self, event=None):
        if self.callback_targets:
            for callback in self.callback_targets:
                callback(self.get_selected())

    def treeview_sort_column(self, tv, col, reverse):
        """
        https://stackoverflow.com/questions/1966929/tk-treeview-column-sort
        :param tv:
        :param col:
        :param reverse:
        :return:
        """
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        l.sort(reverse=reverse)

        # rearrange items in sorted positions
        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)

        # reverse sort next time
        tv.heading(col, command=lambda: self.treeview_sort_column(tv, col, not reverse))

    def get_selected(self):
        selection = self.tree.selection()
        item_dict = self.tree.item(selection)
        # print('item_dict', item_dict)
        return_dict = {}
        for k, col in enumerate(self.columns):
            if k==0:
                return_dict[col] = item_dict['text']
            else:
                try:
                    return_dict[col] = item_dict['values'][k-1]
                except:
                    return_dict[col] = ''
        return return_dict

    def reset_tree(self):
        """
        Deletes all items in the treeview.
        :return:
        """
        for i in self.tree.get_children():
            self.tree.delete(i)

    def set_treeview_dict(self, treeview_dict):
        """
        Sets the treeview widget with data from the treeview_dict. Structur is:

        {'First': 'children': {'Second': 'children: {...},
                                         'value': 'Test string'}
        Where 'value' must be initiated as a column in the treview widget.

        :param treeview_dict:
        :return:
        """
        def add_level(parent, level_dict):
            for name in utils.sorted_int(level_dict):
                key = '{}_{}'.format(parent, name)
                self.tree.insert(parent, 'end', key, text=name)
                if 'children' in level_dict[name]:
                    add_level(key, level_dict[name]['children'])

                for col in level_dict[name]:
                    if col == 'value':
                        header = '#1'
                        self.tree.set(key, header, level_dict[name][col])
                    elif col.startswith('col'):
                        header = col.replace('col', '#')
                        self.tree.set(key, header, level_dict[name][col])

        # First delete old entries
        self.reset_tree()

        # Then add new data
        add_level('', treeview_dict)

        # Add sorting functionality (not working yet)
        #for col in self.columns:
        #    self.tree.heading(col, text=col, command=lambda: self.treeview_sort_column(self.tree, col, False))


class MenuWidget(object):

    def __init__(self,
                 parent,
                 bind_command="<Button-3>",
                 bind_widget=None,
                 bind_fig=None,
                 items=[],
                 **kwargs):

        self.parent = parent
        self.bind_widget = bind_widget
        self.bind_fig = bind_fig
        self.kwargs = kwargs

        self.popup_menu = tk.Menu(self.parent, tearoff=0)
        for k, item in enumerate(items):
            self.popup_menu.add_command(label=item.get('label', item.get('text', item.get('name', str(k)))),
                                        command=item.get('target', item.get('command', None)))

        if bind_widget:
            bind_widget.bind(bind_command, self.popup)  # Button-2 on Aqua
        elif bind_fig:
            bind_fig.canvas.mpl_connect(bind_command, self.popup)

    def popup(self, event):
        popup = True
        if self.bind_fig:
            if self.kwargs.get('button'):
                if self.kwargs.get('button') != event.button:
                    popup = False
            if popup:
                try:
                    print('event.x, event.y', event.x, event.y)
                    disp_cord = self.bind_fig.axes[0].transData.transform([event.x, event.y])
                    x = int(disp_cord[0])
                    y = int(disp_cord[1])
                    print('xx yy', x, y)

                    x = self.parent.winfo_x()
                    y = self.parent.winfo_y()
                    w = self.parent.winfo_width()
                    h = self.parent.winfo_height()
                    print('x y w, h', x, y, w, h)

                    x = int(x + w / 2)
                    y = int(y + h / 2)

                    print('X Y', x, y)

                    self.popup_menu.tk_popup(x, y, 0)
                finally:
                    self.popup_menu.grab_release()

        elif self.bind_widget:
            try:
                print('X Y', event.x_root, event.y_root)
                self.popup_menu.tk_popup(event.x_root, event.y_root, 0)
            finally:
                self.popup_menu.grab_release()

class Fonts():
    def __init__(self):
        self.fontsize_small = font.Font(size=6)
        self.fontsize_medium = font.Font(size=8)
        self.fontsize_large = font.Font(size=10)
           
"""
================================================================================
================================================================================
================================================================================
""" 
class TestApp(tk.Tk):
    #===========================================================================
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs) 

        self._set_start_frame()
        
#         self._set_frame_entry()
        self._set_frame_time()
        self._set_frame_treeview()
        
      
    #========================================================================== 
    def _set_start_frame(self):
        self.notebook_widget = NotebookWidget(self, frames=['Time', 'Entry grid', 'Entry', 'Treeview'])
        grid_configure(self)

    def _set_frame_treeview(self):
        frame = self.notebook_widget.frame_treeview
        self.tree = TreeviewWidget(frame)

        grid_configure(frame)
        
    #========================================================================== 
    def _set_frame_time(self):
        frame = self.notebook_widget.frame_time
        
        self.time_widget = TimeWidget(frame, 
                                      title='START time', 
                                      show_header=True, 
                                      row=0,
                                      padx=20, 
                                      sticky='s')
        
        self.time_widget2 = TimeWidget(frame, 
                                      title='STOP time', 
                                      show_header=True, 
                                      row=1, 
                                      padx=10, 
                                      sticky='n')
        start_time = '20160405'
        end_time = '20170101'
        
        self.time_widget.set_valid_time_span(start_time, end_time)
        self.time_widget.set_time(start_time)
        grid_configure(frame, nr_rows=2)
        
        
    #========================================================================== 
    def _set_frame_entry(self):
        frame = self.notebook_widget.frame_entry
        
        return_direction = 'vertical'
        
        nr_rows = 3
        nr_cols = 3
        
        # Create entries
        entries = {}
        for row in range(nr_rows):
            entries[row] = {}
            for col in range(nr_cols):
                ent = EntryWidget(frame, row=row, column=col, entry_id='%s:%s' %(row, col))
                ent.set_return_direction(return_direction) # This is overrideed in a later stage
                entries[row][col] = ent
        
        # Link entries
        for row in range(nr_rows):
            for col in range(nr_cols):
                # Check row
                north_row = row-1
                south_row = row+1
                north_col = col
                south_col = col
                if row == 0:
                    north_row = nr_rows-1
                elif row == nr_rows-1:
                    south_row = 0
                
                # Check col
                west_col = col-1
                east_col = col+1
                west_row = row 
                east_row = row
                if col == 0:
                    west_col = nr_cols-1
                elif col == nr_cols-1:
                    east_col = 0
                    
                # Orientation keys
                entries[row][col].north_entry = entries[north_row][north_col]
                entries[row][col].south_entry = entries[south_row][south_col]
                entries[row][col].west_entry = entries[west_row][west_col]
                entries[row][col].east_entry = entries[east_row][east_col]
                
                # Return key
                if return_direction == 'horizontal':
                    return_row = east_row
                    return_col = east_col
                    if col == nr_cols-1:
                        return_row = row + 1
                        if return_row == nr_rows:
                            return_row = 0
                elif return_direction == 'vertical':
                    return_row = south_row
                    return_col = south_col
                    if row == nr_rows-1:
                        return_col = col + 1
                        if return_col == nr_cols:
                            return_col = 0
                            
                entries[row][col].return_entry = entries[return_row][return_col]



def disable_widgets(*args):
    for arg in args:
        arg.config(state='disabled')


def enable_widgets(*args):
    for arg in args:
        arg.config(state='normal')


def get_calendar(locale, fwday):
    # instantiate proper calendar class
    if locale is None:
        return calendar.TextCalendar(fwday)
    else:
        return calendar.LocaleTextCalendar(fwday, locale)

"""
================================================================================
================================================================================
================================================================================
""" 
def grid_configure(frame, nr_rows=1, nr_columns=1, **kwargs):
    """
    Updated 20180825     
    
    Put weighting on the given frame. Put weighting on the number of rows and columns given. 
    kwargs with tag "row"(r) or "columns"(c, col) sets the number in tag as weighting. 
    Example: 
        c1=2 sets frame.grid_columnconfigure(1, weight=2)
    """
    row_weight = {}
    col_weight = {}
    
    # Get information from kwargs 
    for key, value in kwargs.items():
        rc = int(re.findall('\d+', key)[0])
        if 'r' in key:
            row_weight[rc] = value
        elif 'c' in key:
            col_weight[rc] = value 
                      
    # Set weight 
    for r in range(nr_rows): 
        frame.grid_rowconfigure(r, weight=row_weight.get(r, 1))
        
    for c in range(nr_columns):
        frame.grid_columnconfigure(c, weight=col_weight.get(c, 1))

        
        
def set_aspect(content_frame, pad_frame, aspect_ratio):
    # a function which places a frame within a containing frame, and
    # then forces the inner frame to keep a specific aspect ratio

    def enforce_aspect_ratio(event):
        # when the pad window resizes, fit the content into it,
        # either by fixing the width or the height and then
        # adjusting the height or width based on the aspect ratio.

        # start by using the width as the controlling dimension
        desired_width = event.width
        desired_height = int(event.width / aspect_ratio)

        # if the window is too tall to fit, use the height as
        # the controlling dimension
        if desired_height > event.height:
            desired_height = event.height
            desired_width = int(event.height * aspect_ratio)

        # place the window, giving it an explicit size
        content_frame.place(in_=pad_frame, x=0, y=0,
            width=desired_width, height=desired_height)

    pad_frame.bind("<Configure>", enforce_aspect_ratio)
     
     
"""
================================================================================
================================================================================
================================================================================
""" 
def check_path_entry(stringvar, return_string=False):
    """
    Gets a tk.StringVar and sets it so that its only possible to enter float numbers. 
    """

    sv = False
    if isinstance(stringvar, tk.StringVar):
        sv = stringvar
    else:
        for item in stringvar:
            # If tuple is given. Often from tk.StringVar().trace()
            if isinstance(item, tk.StringVar):
                sv = item
                break
            
    if sv:
        string = sv.get()
        # string = string.replace('\\', '/').rstrip('/')
        string = string.replace('\\', '/')
        sv.set(string)
        
        if return_string:
            return return_string
     
"""
================================================================================
================================================================================
================================================================================
""" 
def check_int_entry(stringvar, return_string=False):
    """
    Gets a tk.StringVar and sets it so that its only possible to enter float numbers. 
    """

    sv = False
    if isinstance(stringvar, tk.StringVar):
        sv = stringvar
    else:
        for item in stringvar:
            # If tuple is given. Often from tk.StringVar().trace()
            if isinstance(item, tk.StringVar):
                sv = item
                break
            
    if sv:
        string = sv.get()
        string = re.sub('[^0-9]', '', string)
        string = string.lstrip('0')
        sv.set(string)
        
        if return_string:
            return return_string
        
"""
================================================================================
================================================================================
================================================================================
""" 
def check_float_entry(stringvar, entry, only_negative_values=False, return_string=False):
    """
    Gets a tk.StringVar and sets it so that its only possible to enter float numbers. 
    """

    sv = False
    if isinstance(stringvar, tk.StringVar):
        sv = stringvar
    else:
        for item in stringvar:
            # If tuple is given. Often from tk.StringVar().trace()
            if isinstance(item, tk.StringVar):
                sv = item
                break
    
    if sv:
        string = sv.get()
        string = string.replace(',', '.')
        new_char_list = []
        for i, s in enumerate(string):
            if i==0 and s=='-':
                new_char_list.append(s)
            elif s=='.' and '.' not in new_char_list:
                new_char_list.append(s)
            elif s.isdigit():
                new_char_list.append(s)
                
        new_string = ''.join(new_char_list)
        
        if len(new_string) > 1 and new_string.count('0') == len(new_string):
            new_string = '0'
        if new_string and only_negative_values and new_string != '0' and not new_string.startswith('-'):
            new_string = '-'+new_string
        sv.set(new_string)
        
        entry.icursor('end')
        entry.xview('end')
#         entry.icursor(len(new_string)+10)
        
        if return_string:
            return return_string


def disable_buttons_in_class(cls, keep_button=None):
    bg_color = tk.Button().cget('bg')
    for key, widget in cls.__dict__.items():
        if not isinstance(widget, tk.Button):
            continue
        widget.config(state='disabled', bg=bg_color)
        widget.update_idletasks()
    if keep_button:
        keep_button.config(state='normal')


def enable_buttons_in_class(cls):
    bg_color = tk.Button().cget('bg')
    for key, widget in cls.__dict__.items():
        if not isinstance(widget, tk.Button):
            continue
        widget.config(state='normal', bg=bg_color)
        widget.update_idletasks()