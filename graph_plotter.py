import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator
import json

TEST_DATA =  {
            'Ben2508#6969': 
                {
                '2021-01-14': [1, 200, 423],
                '2021-01-15': [2, 331, 200],
                '2021-01-16': [4, 504, 373]
                }, 
            'Bella Diamondtiger#3608': 
                {
                '2021-01-14': [1, 412, 123],
                '2021-01-15': [2, 231, 300],
                '2021-01-16': [3, 304, 562]
                }
            }

FILE_PATH = "C:\\Users\\matan\\Desktop\\Coding\\Python\\Graph Plotter\\data.json"

testing = False

if not testing:
    file = open(FILE_PATH, "r")
    RAW_DATA = json.load(file)
    file.close()
else:   
    RAW_DATA = TEST_DATA

DATA = {}
Y_LABEL = {}
Y_LABEL['Messages Sent'] = "Messages"
Y_LABEL['Call Time'] = "Time (seconds)"
Y_LABEL['Online Time'] = "Time (seconds)"
for name in RAW_DATA:
    DATA[name] = {}
    DATA[name]['Messages Sent'] = []
    DATA[name]['Call Time'] = []
    DATA[name]['Online Time'] = []
    for date in RAW_DATA[name]:
        DATA[name]['Messages Sent'].append(RAW_DATA[name][date][0])
        DATA[name]['Call Time'].append(RAW_DATA[name][date][1])
        DATA[name]['Online Time'].append(RAW_DATA[name][date][2])

def main(graph):
    fig, ax = plt.subplots(figsize=(10,7))
    ax.set_title(graph)
    plt.ylabel(Y_LABEL[graph])
    plt.xlabel('Days')
    ax = fig.gca()
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    for name in DATA:
        x = []
        y =[]
        for p, q in enumerate(DATA[name][graph]):
            x.append(p)
            y.append(q)
        ax.plot(x, y, label=name)

    ax.legend(loc='upper left', bbox_to_anchor=(1.05, 1),
              ncol=2, borderaxespad=0)
    fig.subplots_adjust(right=0.55)
    fig.suptitle('Right-click to hide all\nMiddle-click to show all',
                 va='top', size='large')

    leg = interactive_legend()
    return fig, ax, leg

def interactive_legend(ax=None):
    if ax is None:
        ax = plt.gca()
    if ax.legend_ is None:
        ax.legend()

    return InteractiveLegend(ax.get_legend())

class InteractiveLegend(object):
    def __init__(self, legend):
        self.legend = legend
        self.fig = legend.axes.figure

        self.lookup_artist, self.lookup_handle = self._build_lookups(legend)
        self._setup_connections()

        self.update()

    def _setup_connections(self):
        for artist in self.legend.texts + self.legend.legendHandles:
            artist.set_picker(10) # 10 points tolerance

        self.fig.canvas.mpl_connect('pick_event', self.on_pick)
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)

    def _build_lookups(self, legend):
        labels = [t.get_text() for t in legend.texts]
        handles = legend.legendHandles
        label2handle = dict(zip(labels, handles))
        handle2text = dict(zip(handles, legend.texts))

        lookup_artist = {}
        lookup_handle = {}
        for artist in legend.axes.get_children():
            if artist.get_label() in labels:
                handle = label2handle[artist.get_label()]
                lookup_handle[artist] = handle
                lookup_artist[handle] = artist
                lookup_artist[handle2text[handle]] = artist

        lookup_handle.update(zip(handles, handles))
        lookup_handle.update(zip(legend.texts, handles))

        return lookup_artist, lookup_handle

    def on_pick(self, event):
        handle = event.artist
        if handle in self.lookup_artist:

            artist = self.lookup_artist[handle]
            artist.set_visible(not artist.get_visible())
            self.update()

    def on_click(self, event):
        if event.button == 3:
            visible = False
        elif event.button == 2:
            visible = True
        else:
            return

        for artist in self.lookup_artist.values():
            artist.set_visible(visible)
        self.update()

    def update(self):
        for artist in self.lookup_artist.values():
            handle = self.lookup_handle[artist]
            if artist.get_visible():
                handle.set_visible(True)
            else:
                handle.set_visible(False)
        self.fig.canvas.draw()

    def show(self):
        plt.show()

c = "0"
while c != "0":
    c = input("Which graph would you like to load:\n1: Messages Sent\n2: Call Time\n3: Online Time\n0: Exit\nEnter your choice: ")
    if c == "1":
        fig, ax, leg = main('Messages Sent')
        plt.show()
    elif c == "2":
        fig, ax, leg = main('Call Time')
        plt.show()
    elif c == "3":
        fig, ax, leg = main('Online Time')
        plt.show()
    elif c == "0":
        print("Exiting program..")
    else:
        print("Invalid choice")