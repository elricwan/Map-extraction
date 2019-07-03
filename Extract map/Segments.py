# -*- coding: utf-8 -*-
"""
Created on Tue Nov 20 10:23:28 2018

@author: wxp
"""
import osmnx as ox
import networkx as nx
import requests
import matplotlib.cm as cm
import matplotlib.colors as colors
ox.config(use_cache=True, log_console=True)
ox.__version__
# Mahanton.
#Place = 'Hoboken, New Jersey'
Place = 'Manhattan, New York City'
G = ox.graph_from_place(Place, network_type = 'drive')
# length of segments
d = 100

# Remove unnecessary roads and edges
Roads = list(G.edges())
# keep {'primary', 'secondary', 'tertiary', 'residential', 'trunk'} only
for r in Roads:
    key = [a for a in G.adj[r[0]][r[1]].keys()]
    proper = G.adj[r[0]][r[1]][key[0]]['highway']
    if 'motor' in proper or 'motor_link' in proper:
        G.remove_edge(r[0],r[1])
# Node list
Roads = list(G.edges())
node_list = []
for r in Roads:
    node_list.append(r[0])
    node_list.append(r[1])
node_list = set(node_list)
# remove wrong roads with (a,a)
Roads = list(G.edges)
for r in Roads:
    if r[0]==r[1]:
        G.remove_edge(r[0],r[1])
# remove duplicate roads
do = 1
while do > 0:
    store_edge = []
    Roads = list(G.edges())
    for r in Roads:
        if r in store_edge:
            G.remove_edge(r[0],r[1])
        else:
            store_edge.append(r)
    do = len(Roads)-len(G.edges())
# we need an undirected graph to find neighbors of each node
G_undir = G.to_undirected()
# remove dead end and single node
do = 1
while do > 0:
    Nodes = list(G.nodes())
    G_undir = G.to_undirected()
    for n in Nodes:
        if n not in node_list or len([a for a in G_undir.neighbors(n)]) == 1:
            G.remove_node(n)
    do = len(Nodes) - len(G)

# name the road with its order
Roads = list(G.edges())
check_list = {}
for i in range(len(Roads)):
    check_list[Roads[i]] = i + 1
# find the neighborhood road
def find_nei(road):
    Roads = list(G.edges())
    a = road[0]
    b = road[1]
    road_neibor = []
    for r in Roads:
        if r[0] == a or r[0] == b or r[1] == a or r[1] == b:
            road_neibor.append(r)
    return road_neibor
# Since the some speed information are str, some are digit, we need to conver all to digit
def str2num(speed):
    if type(speed) == list: # two data stored in the same road
        speed = speed[0]
    if len(speed) > 4:
        speed = speed[:2]
    return float(speed)
# find the maxspeed of the road
from numpy.random import RandomState
def find_maxspeed(road):
    # some maxspeed stored in the map
    key = [a for a in G.adj[road[0]][road[1]].keys()]
    if 'maxspeed' in G.adj[road[0]][road[1]][key[0]].keys():
        max_speed = str2num(G.adj[road[0]][road[1]][key[0]]['maxspeed'])
    else:
        #exponential distrubution from 25 to 50.
        max_speed = 20 + RandomState().exponential(5)
    return max_speed
# most road has no nl infor, some most of them are generated with exponential distribution
def find_nl(road):
    # some nl stored in the map
    key = [a for a in G.adj[road[0]][road[1]].keys()]
    if 'lanes' in G.adj[road[0]][road[1]][key[0]].keys():
        if len(G.adj[road[0]][road[1]][key[0]]['lanes']) > 1: # some roads has different lanes per segment, choose the first one
            lanes = int(G.adj[road[0]][road[1]][key[0]]['lanes'][0])
        else:
            lanes = int(G.adj[road[0]][road[1]][key[0]]['lanes'])
    else:
        lanes = round(1 + RandomState().exponential(0.5))
        lanes = min(lanes,4)
    return lanes
# define segments
import json
import math
import statistics
n_intersection = len(G.nodes())
n_road = len(G.edges())
Region = {}
Region['Intersection'] = {}
for i in range(n_intersection):
    Intersect = list(G.nodes())[i]
    Region['Intersection'][Intersect] = G.node[Intersect]
Region['Segment'] = {}
for i in range(n_road):
    road = list(G.edges())[i]
    Region['Segment'][road] = {}
    key = [a for a in G.adj[road[0]][road[1]].keys()]
    # the length information is stored in graph
    distance = G.adj[road[0]][road[1]][key[0]]['length']
    lanes = find_nl(road)
    max_speed = find_maxspeed(road)
        
    # number of subsegments for each road
    num_sub =  int(round(distance/d))
    if num_sub == 0:
        num_sub = 1
    Region['Segment'][road]['num_sub'] = num_sub
    # Number of lanes and maximum speed for the road
    Region['Segment'][road]['lanes'] = lanes
    Region['Segment'][road]['maxspeed'] = max_speed
    # name the road with its order
    Region['Segment'][road]['id'] = check_list[road]
    Region['Segment'][road]['subs'] = []
    # define x,y for each road
    x1 = Region['Intersection'][road[0]]['x']
    x2 = Region['Intersection'][road[1]]['x']
    y1 = Region['Intersection'][road[0]]['y']
    y2 = Region['Intersection'][road[1]]['y']
    Region['Segment'][road]['X'] = [x1,x2]
    Region['Segment'][road]['Y'] = [y1,y2]
    # define stop probability
    Region['Segment'][road]['probability'] = 0
    for j in range(num_sub):
        sub_distance = distance/num_sub
        # define x,y for each road subsegment
        a1 = Region['Intersection'][road[0]]['x'] + \
        j*(Region['Intersection'][road[1]]['x'] - Region['Intersection'][road[0]]['x'])/num_sub
        a2 = Region['Intersection'][road[0]]['x'] + \
        (j+1)*(Region['Intersection'][road[1]]['x'] - Region['Intersection'][road[0]]['x'])/num_sub # x coordiante for fist segment
        
        b1 = Region['Intersection'][road[0]]['y'] + \
        j*(Region['Intersection'][road[1]]['y'] - Region['Intersection'][road[0]]['y'])/num_sub
        b2 = Region['Intersection'][road[0]]['y'] + \
        (j+1)*(Region['Intersection'][road[1]]['y'] - Region['Intersection'][road[0]]['y'])/num_sub
        
        #Region['Segment'][road]['sub'+ str(j)] = {'x':[a1,a2] ,'y':[b1,b2], 'uturn': 0}
        Region['Segment'][road]['subs'] += [{'x':[a1,a2] ,'y':[b1,b2], 'distance':sub_distance,'uturn': 0}]
# Add In-Out to intersection
for i in range(n_intersection):
    # the name of the road is the order of the road
    Intersect = list(G.nodes())[i]
    Roads = list(G.edges())
    Out = [i+1 for i in range(n_road) if Roads[i][0] == Intersect]
    In = [i+1 for i in range(n_road) if Roads[i][1] == Intersect]
    
    Region['Intersection'][Intersect]['In'] = In
    Region['Intersection'][Intersect]['Out'] = Out
# Find the corresponding uturn road
import numpy as np
To_road = list(Region['Segment'].keys())
for road in To_road:
    key = [a for a in G.adj[road[0]][road[1]].keys()]
    if G.adj[road[0]][road[1]][key[0]]['oneway'] != True:
        i = road[::-1]
        for road_seg in range(Region['Segment'][road]['num_sub']-1):
            target_x = Region['Segment'][road]['subs'][road_seg]['x'][::-1]
            target_y = Region['Segment'][road]['subs'][road_seg]['y'][::-1]
            dis = []
            for j in range(Region['Segment'][i]['num_sub']):  # we do not consider the segment into intersection
                x1 = Region['Segment'][i]['subs'][j]['x'][0]
                x2 = Region['Segment'][i]['subs'][j]['x'][1]
                y1 = Region['Segment'][i]['subs'][j]['y'][0]
                y2 = Region['Segment'][i]['subs'][j]['y'][1]
                # find the minimum dist from the street's end to the uturn's start
                dis.append((target_x[0] - x1)**2 + (target_y[0] - y1)**2)
            if len(dis) > 0:
                ind = np.argmin(dis)
                ind = int(ind)
                # Transform the road to its name, et, its order in the list.
                # add one because in matlab everything go from 1
                raod_name = check_list[i]
                Region['Segment'][road]['subs'][road_seg]['uturn'] = [raod_name,ind+1]    
                
# add event
import random
for i in range(n_road):
    r = list(G.edges())[i]
    Event = [0] * 5000
    if random.random() < 0.1: # 10% probability to have events
        start = random.randint(1,n_road-300) 
        duration = random.randint(30,500)
        end = min(500,start+duration)
        Event[start:end] = [1]*(end-start)
        Region['Segment'][r]['Event'] = Event
    else:
        Region['Segment'][r]['Event'] = Event   
# Output json file
# First I need to transform every key to str
Intersection = Region['Intersection']
with open('Intercept.json', 'w') as outfile:
    json.dump(Intersection, outfile)
# Output json file
# First I need to transform every key to str
Segment = dict([(str(a).replace(' ','')[1:-1],b) for (a,b) in Region['Segment'].items()])
Intersection = Region['Intersection']
with open('Segment.json', 'w') as outfile:  
    json.dump(Segment, outfile)
