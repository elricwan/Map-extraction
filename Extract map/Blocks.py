# -*- coding: utf-8 -*-
"""
Created on Tue Nov 20 10:02:40 2018

@author: wxp
"""
import osmnx as ox, networkx as nx, numpy as np
import pandas as pd
ox.config(log_console=True, use_cache=True)

Place = '345 W 35th St, New York, New York'
Distance = 400
# Extract map
B = ox.buildings.buildings_from_address(Place,distance=Distance, retain_invalid=False)
G = ox.graph_from_address(Place, network_type='drive',distance=Distance)
# Obtain heights information
centroidseries = B['geometry'].centroid
df = pd.concat([centroidseries.x, centroidseries.y,B['height']], axis=1)
df.columns = ['x','y','height']
df = df.dropna()
# Remove unnecessary roads and nodes
Roads = list(G.edges())
# keep {'primary', 'secondary', 'tertiary', 'residential', 'trunk'} only
for r in Roads:
    proper = G.adj[r[0]][r[1]][0]['highway']
    if 'motor' in proper or 'motor_link' in proper:
        G.remove_edge(r[0],r[1])
# Node list
Roads = list(G.edges())
node_list = []
for r in Roads:
    node_list.append(r[0])
    node_list.append(r[1])
node_list = set(node_list)
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
# remove the point that has only two neighbors and is not the boundary point
do = 1
while do > 0:
    Nodes = list(G.nodes())
    G_undir = G.to_undirected()
    for n in Nodes:
        nei = [a for a in G_undir.neighbors(n)]
        if len(nei) == 2:
            slope1 = (G_undir.node[nei[0]]['y']-G_undir.node[n]['y'])/(G_undir.node[nei[0]]['x']-G_undir.node[n]['x'])
            slope2 = (G_undir.node[nei[1]]['y']-G_undir.node[n]['y'])/(G_undir.node[nei[1]]['x']-G_undir.node[n]['x'])
            diff = slope1 - slope2
            if -0.1 < diff < 0.1:
                # remove that node but keep the edges
                G.remove_node(n)
                G.add_edge(nei[0],nei[1])
                break
    do = len(Nodes) - len(G)
# Create polygon of the block
def slope_cal(a,b,n):
    slope1 = (G_undir.node[a]['y']-G_undir.node[n]['y'])/(G_undir.node[a]['x']-G_undir.node[n]['x'])
    slope2 = (G_undir.node[b]['y']-G_undir.node[n]['y'])/(G_undir.node[b]['x']-G_undir.node[n]['x'])
    diff = slope1 - slope2
    return diff

block = []
for n in Nodes:
    nei = [a for a in G_undir.neighbors(n)]
    G_test = G_undir.copy()
    G_test.remove_node(n)
    if len(nei) == 2:
        path = nx.bidirectional_shortest_path(G_test, nei[0],nei[1])
        box = [n] + path
        block.append(box)
    elif len(nei) == 3:
        diff1 = slope_cal(nei[0],nei[1],n)
        diff2 = slope_cal(nei[0],nei[2],n)
        diff3 = slope_cal(nei[1],nei[2],n)
        if abs(diff1) > 0.1:
            path1 = nx.bidirectional_shortest_path(G_test, nei[0],nei[1])
            box1 = [n] + path1
            block += [box1]
        if abs(diff2) > 0.1:
            path2 = nx.bidirectional_shortest_path(G_test, nei[0],nei[2])
            box2 = [n] + path2
            block += [box2]
        if abs(diff3) > 0.1:
            path3 = nx.bidirectional_shortest_path(G_test, nei[1],nei[2])
            box3 = [n] + path3
            block += [box3]
    elif len(nei) == 4:
        diff1 = slope_cal(nei[0],nei[1],n)
        diff2 = slope_cal(nei[0],nei[2],n)
        diff3 = slope_cal(nei[0],nei[3],n)
        diff4 = slope_cal(nei[1],nei[2],n)
        diff5 = slope_cal(nei[1],nei[3],n)
        diff6 = slope_cal(nei[2],nei[3],n)
        if abs(diff1) > 0.1:
            path1 = nx.bidirectional_shortest_path(G_test, nei[0],nei[1])
            box1 = [n] + path1
            block += [box1]
        if abs(diff2) > 0.1:
            path2 = nx.bidirectional_shortest_path(G_test, nei[0],nei[2])
            box2 = [n] + path2
            block += [box2]
        if abs(diff3) > 0.1:
            path3 = nx.bidirectional_shortest_path(G_test, nei[0],nei[3])
            box3 = [n] + path3
            block += [box3]
        if abs(diff4) > 0.1:
            path4 = nx.bidirectional_shortest_path(G_test, nei[1],nei[2])
            box4 = [n] + path4
            block += [box4]
        if abs(diff5) > 0.1:
            path5 = nx.bidirectional_shortest_path(G_test, nei[1],nei[3])
            box5 = [n] + path5
            block += [box5]
        if abs(diff6) > 0.1:
            path6 = nx.bidirectional_shortest_path(G_test, nei[2],nei[3])
            box6 = [n] + path6
            block += [box6]   

# remove duplicate blocks
from collections import Counter
a_list = []
new_block = []
for b in block:
    if Counter(b) not in a_list:
        a_list.append(Counter(b))
        new_block.append(b)
        
# Remove the large blocks that comprised of small blocks
block_4 = [b for b in new_block if len(b) == 4]
block_3 = [b for b in new_block if len(b) == 3]
block_small = block_3 + block_4
block_large = []
for b in new_block:
    add = 1
    if len(b) > 4:
        key = list(Counter(b).keys())
        for b_small in block_small:
            key_small = list(Counter(b_small).keys())
            if all(elem in key for elem in key_small):  # the big block contains that small block
                add = 0
                break
        if add == 1:
            block_large.append(b)
            
# Now is the final blocks that has adjoint with each other
new_block = block_small + block_large
# Define edges for blocks
def obtain_edge(b):
    edges = []
    b = b + [b[0]]
    n = len(b)
    for i in range(n-1):
        edges = edges + [(b[i],b[i+1]),(b[i+1],b[i])]
    return edges
# Create polygon and add heights
# Save the block information to the json file
# The information includes the nodes, edges, heights and coords.
import sys
import json
from shapely.geometry import Point
from shapely.geometry import Polygon
from shapely.geometry import asShape
from shapely.geometry import mapping
Block = {}
for i in range(len(new_block)):
    b = new_block[i]
    Block[i] = {}
    Block[i]['nodes'] = b
    Block[i]['edges'] = obtain_edge(b)
    coords = [(G_undir.node[n]['x'],G_undir.node[n]['y']) for n in b]
    Block[i]['coords'] = coords
    Block[i]['height'] = 0
    poly = Polygon(coords)
    for j in range(len(df)):
        x, y, height = df.iloc[j]['x'], df.iloc[j]['y'], float(df.iloc[j]['height'])
        point = Point(x, y)
        if poly.contains(point):
            Block[i]['height'] = height
            break
# Output json file
with open('Block.json', 'w') as outfile:
    json.dump(Block, outfile)
    
# Assume there are three layers
h1 = 5
h2 =15
h3 = 35
# find all the nodes first
Node = []
for b in new_block:
    Node += b
Node = list(set(Node))
import itertools
def complete_edge(b):
    edges = [a for a in itertools.combinations(b, 2)] + [a[::-1] for a in itertools.combinations(b, 2)]
    return edges
# Roads on layer 1
Edges_1 = []
for i in range(len(Block)):
    # cannot crossover
    if Block[i]['height'] > h1:
        Edges_1 += Block[i]['edges']
    # crossover
    else:
        edges = complete_edge(Block[i]['nodes'])
        Edges_1 += edges
Edges_1 = list(set(Edges_1))
Edges_1 = [(a[0],a[1],1) for a in Edges_1]
# Roads on layer 2
Edges_2 = []
for i in range(len(Block)):
    # cannot crossover
    if Block[i]['height'] > h2:
        Edges_2 += Block[i]['edges']
    # crossover
    else:
        edges = complete_edge(Block[i]['nodes'])
        Edges_2 += edges
Edges_2 = list(set(Edges_2))   
Edges_2 = [(a[0],a[1],2) for a in Edges_2]
# Roads on layer 3
Edges_3 = []
for i in range(len(Block)):
    # cannot crossover
    if Block[i]['height'] > h3:
        Edges_3 += Block[i]['edges']
    # crossover
    else:
        edges = complete_edge(Block[i]['nodes'])
        Edges_3 += edges
Edges_3 = list(set(Edges_3))  
Edges_3 = [(a[0],a[1],3) for a in Edges_3]
# define the new edge that come from the lower layer to higher layer
Edges_4 = [(a,a,1.2) for a in Node]
Edges_5 = [(a,a,2.2) for a in Node]
# define the new edge that come from the higher layer to lower layer
Edges_6 = [(a,a,1.8) for a in Node]
Edges_7 = [(a,a,2.8) for a in Node]
Total_edges = Edges_1 + Edges_2 + Edges_3 + Edges_4 + Edges_5 + Edges_6 + Edges_7
Segment = {}
for i in range(len(Total_edges)):
    r = Total_edges[i]
    Segment[i] = {}
    Segment[i]['road'] = r
    if r[2] == 1:
        Segment[i]['height'] = h1
    if r[2] == 1.2:
        Segment[i]['height'] = h1 + 0.2*(h2-h1)
    if r[2] == 1.8:
        Segment[i]['height'] = h1 + 0.8*(h2-h1)
    if r[2] == 2:
        Segment[i]['height'] = h2
    if r[2] == 2.2:
        Segment[i]['height'] = h2 + 0.2*(h3-h2)
    if r[2] == 2.8:
        Segment[i]['height'] = h2 + 0.8*(h3-h2)
    if r[2] == 3:
        Segment[i]['height'] = h3
    Segment[i]['x'] = [G_undir.node[r[0]]['x'],G_undir.node[r[1]]['x']]
    Segment[i]['y'] = [G_undir.node[r[0]]['y'],G_undir.node[r[1]]['y']]
# Output json file
with open('Segment.json', 'w') as outfile:
    json.dump(Segment, outfile)
# Also three layers of intersection
Node_1 = [(a,1) for a in Node]
Node_2 = [(a,2) for a in Node]
Node_3 = [(a,3) for a in Node]
Total_node = Node_1 + Node_2 + Node_3
Intersection = {}
for i in range(len(Total_node)):
    Intersection[i] = {}
    n = Total_node[i]
    Intersection[i]['intersection'] = n
    Intersection[i]['x'] = G_undir.node[n[0]]['x']
    Intersection[i]['y'] = G_undir.node[n[0]]['y']
    # First layer
    if n[1] == 1:
        In = [j+1 for j in range(len(Total_edges)) if (Total_edges[j][2] == 1 and Total_edges[j][1] == n[0])
                                        or (Total_edges[j][2] == 1.8 and Total_edges[j][1] == n[0])]
        Out = [j+1 for j in range(len(Total_edges)) if (Total_edges[j][2] == 1 and Total_edges[j][0] == n[0])
                                        or (Total_edges[j][2] == 1.2 and Total_edges[j][0] == n[0])]
        Intersection[i]['In'] = In
        Intersection[i]['Out'] = Out
    # Second layer
    elif n[1] == 2:
        In = [j+1 for j in range(len(Total_edges)) if (Total_edges[j][2] == 2 and Total_edges[j][1] == n[0])
                                        or (Total_edges[j][2] == 1.2 and Total_edges[j][1] == n[0]) or
                                             (Total_edges[j][2] == 2.8 and Total_edges[j][1] == n[0])]
        Out = [j+1 for j in range(len(Total_edges)) if (Total_edges[j][2] == 2 and Total_edges[j][0] == n[0])
                                        or (Total_edges[j][2] == 2.2 and Total_edges[j][0] == n[0]) or
                                              (Total_edges[j][2] == 1.8 and Total_edges[j][0] == n[0])]
        Intersection[i]['In'] = In
        Intersection[i]['Out'] = Out
    # Third layer
    else:
        In = [j+1 for j in range(len(Total_edges)) if (Total_edges[j][2] == 3 and Total_edges[j][1] == n[0])
                                        or (Total_edges[j][2] == 2.2 and Total_edges[j][1] == n[0])]
        Out = [j+1 for j in range(len(Total_edges)) if (Total_edges[j][2] == 3 and Total_edges[j][0] == n[0])
                                        or (Total_edges[j][2] == 2.8 and Total_edges[j][0] == n[0])]
        Intersection[i]['In'] = In
        Intersection[i]['Out'] = Out
# Output json file
with open('Intersection.json', 'w') as outfile:
    json.dump(Intersection, outfile)