import numpy as np
import awkward
from graph import Graph
from scipy.spatial import cKDTree
from scipy.spatial import Delaunay
from scipy.sparse import csr_matrix, find
from sklearn.neighbors import NearestNeighbors
from itertools import tee

def make_graph_kdtree(coords,layers,sim_indices,r):
    #setup kd tree for fast processing
    the_tree = cKDTree(coords)
    
    #define the pre-processing (all layer-adjacent hits in ball R < r)
    #and build a sparse matrix representation, then blow it up 
    #to the full R_in / R_out definiton
    pairs = the_tree.query_pairs(r=r,output_type='ndarray')
    first,second = pairs[:,0],pairs[:,1]  
    #selected index pair list that we label as connected
    #pairs_sel  = pairs[( (np.abs(layers[(second,)]-layers[(first,)]) <= 1)  )]
    neighbour_counts = np.unique(pairs[:,0], return_counts=True)[1]
    neighbour_counts = np.repeat(neighbour_counts, neighbour_counts)
    pairs_sel  = pairs[(np.abs(layers[(second,)]-layers[(first,)]) <= 1) | (neighbour_counts == 1)]
    #pairs_sel  = pairs
    data_sel = np.ones(pairs_sel.shape[0])
    
    #prepare the input and output matrices (already need to store sparse)
    r_shape = (coords.shape[0],pairs.shape[0])
    eye_edges = np.arange(pairs_sel.shape[0])
    
    R_i = csr_matrix((data_sel,(pairs_sel[:,1],eye_edges)),r_shape,dtype=np.uint8)
    R_o = csr_matrix((data_sel,(pairs_sel[:,0],eye_edges)),r_shape,dtype=np.uint8)
        
    #now make truth graph y (i.e. both hits are sim-matched)    
    y = (np.isin(pairs_sel,sim_indices).astype(np.int8).sum(axis=-1) == 2)
    
    return R_i,R_o,y

def make_graph_knn(coords, layers, sim_indices, k):
    
    nbrs = NearestNeighbors(algorithm='kd_tree').fit(coords)
    pairs = np.array(nbrs.kneighbors_graph(coords, k).nonzero()).T
    first,second = pairs[:,0],pairs[:,1]  
    #selected index pair list that we label as connected
    pairs_sel  = pairs[(first != second)]
    data_sel = np.ones(pairs_sel.shape[0])
    
    #prepare the input and output matrices (already need to store sparse)
    r_shape = (coords.shape[0],pairs.shape[0])
    eye_edges = np.arange(pairs_sel.shape[0])
    
    R_i = csr_matrix((data_sel,(pairs_sel[:,1],eye_edges)),r_shape,dtype=np.uint8)
    R_o = csr_matrix((data_sel,(pairs_sel[:,0],eye_edges)),r_shape,dtype=np.uint8)
        
    #now make truth graph y (i.e. both hits are sim-matched)    
    y = (np.isin(pairs_sel,sim_indices).astype(np.int8).sum(axis=-1) == 2)
    return R_i,R_o,y    
        


def make_graph_xy(arrays, valid_sim_indices, ievt, mask, r, algo=make_graph_knn):
   
    x = arrays[b'rechit_x'][ievt][mask]
    y = arrays[b'rechit_y'][ievt][mask]
    z = arrays[b'rechit_z'][ievt][mask]
    layer = arrays[b'rechit_layer'][ievt][mask]
    time = arrays[b'rechit_time'][ievt][mask]
    energy = arrays[b'rechit_energy'][ievt][mask]    
    feats = np.stack((x,y,layer,time,energy)).T


    all_sim_hits = np.unique(valid_sim_indices[ievt].flatten())
    sim_hits_mask = np.zeros(arrays[b'rechit_z'][ievt].size, dtype=np.bool)
    sim_hits_mask[all_sim_hits] = True
    simmatched = np.where(sim_hits_mask[mask])[0]
    
    Ri, Ro, y_label = algo(np.stack((x,y,layer)).T, layer, simmatched, r=r)
    
    return Graph(feats, Ri, Ro, y_label, simmatched)

def make_graph_etaphi(arrays, valid_sim_indices, ievt, mask, r, layered_norm, algo=make_graph_knn):
   
    x = arrays[b'rechit_x'][ievt][mask]
    y = arrays[b'rechit_y'][ievt][mask]
    z = arrays[b'rechit_z'][ievt][mask]
    layer = arrays[b'rechit_layer'][ievt][mask]
    time = arrays[b'rechit_time'][ievt][mask]
    energy = arrays[b'rechit_energy'][ievt][mask]    
    feats = np.stack((x,y,layer,time,energy)).T

    eta = arrays[b'rechit_eta'][ievt][mask]
    phi = arrays[b'rechit_phi'][ievt][mask]
    layer_normed = layer / layered_norm
    
    all_sim_hits = np.unique(valid_sim_indices[ievt].flatten())
    sim_hits_mask = np.zeros(arrays[b'rechit_z'][ievt].size, dtype=np.bool)
    sim_hits_mask[all_sim_hits] = True
    simmatched = np.where(sim_hits_mask[mask])[0]
    
    #Ri, Ro, y_label = make_graph_kdtree(np.stack((eta, phi, layer_normed)).T, layer, simmatched, r=r)
    Ri, Ro, y_label = algo(np.stack((eta, phi, layer_normed)).T, layer, simmatched, k=5)
    
    return Graph(feats, Ri, Ro, y_label, simmatched)