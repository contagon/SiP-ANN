'''
 SiP.py - A library of different silicon photonic device compact models
 leveraging artificial neural networks

Changes                                       (Author) (Date)
  Initilization .............................. (AMH) - 22-01-2019

Current devices:                              (Author)(Date last modified)
  Straight waveguide (TE/TM) ................. (AMH) - 22-01-2019
  Bent waveguide ............................. (AMH) - 22-01-2019
  Evanescent waveguide coupler ............... (AMH) - 22-01-2019
  Racetrack ring resonator ................... (AMH) - 22-01-2019
  Rectangular ring resonator ................. (AMH) - 22-01-2019

'''

# ---------------------------------------------------------------------------- #
# Import libraries
# ---------------------------------------------------------------------------- #
from SiPANN import import_nn
import numpy as np
import skrf as rf
import pkg_resources


# ---------------------------------------------------------------------------- #
# Initialize ANNs
# ---------------------------------------------------------------------------- #

'''
We initialize all of the ANNs as global objects for speed. This is especially
useful for optimization routines and GUI's that need to make several ANN
evaluations quickly.
'''

gapReal_FILE = pkg_resources.resource_filename('SiPANN', 'ANN/GAP_SWEEP_REALS')
ANN_gapReal      = import_nn.ImportNN(gapReal_FILE)

straightReal_FILE = pkg_resources.resource_filename('SiPANN', 'ANN/STRAIGHT_SWEEP_REALS')
ANN_straightReal = import_nn.ImportNN(straightReal_FILE)

# ---------------------------------------------------------------------------- #
# Helper functions
# ---------------------------------------------------------------------------- #

# Generalized N-dimensional products
def cartesian_product(arrays):
    la = len(arrays)
    dtype = np.find_common_type([a.dtype for a in arrays], [])
    arr = np.empty([len(a) for a in arrays] + [la], dtype=dtype)
    for i, a in enumerate(np.ix_(*arrays)):
        arr[..., i] = a
    return arr.reshape(-1, la)

# ---------------------------------------------------------------------------- #
# Strip waveguide
# ---------------------------------------------------------------------------- #

'''
straightWaveguide()

Calculates the analytic scattering matrix of a simple, parallel waveguide
directional coupler using the ANN.

INPUTS:
wavelength .............. [np array](N,) wavelength points to evaluate
width ................... [np array](N,) width of the waveguides in microns
thickness ............... [np array](N,) thickness of the waveguides in microns

OUTPUTS:
S ....................... [np array](N,2,2) Scattering matrix

'''
def straightWaveguide(wavelength,width,thickness,derivative=None):

    # Santize the input
    if type(wavelength) is np.ndarray:
        wavelength = np.squeeze(wavelength)
    else:
        wavelength = np.array([wavelength])
    if type(width) is np.ndarray:
        width = np.squeeze(width)
    else:
        width = np.array([width])
    if type(thickness) is np.ndarray:
        thickness = np.squeeze(thickness)
    else:
        thickness = np.array([thickness])

    # Run through neural network
    INPUT  = cartesian_product([wavelength,width,thickness])

    if derivative is None:
        OUTPUT = ANN_straightReal.output(INPUT)
    else:
        numRows = INPUT.shape[0]
        OUTPUT = np.zeros((numRows,6))
        # Loop through the derivative of all the outputs
        for k in range(6):
            OUTPUT[:,k] = np.squeeze(ANN_straightReal.differentiate(INPUT,d=(k,0,derivative)))

    # process the output
    tensorSize = (wavelength.size,width.size,thickness.size)
    TE0 = np.reshape(OUTPUT[:,0],tensorSize)
    TE1 = np.reshape(OUTPUT[:,1],tensorSize)
    TE2 = np.reshape(OUTPUT[:,2],tensorSize)
    TM0 = np.reshape(OUTPUT[:,3],tensorSize)
    TM1 = np.reshape(OUTPUT[:,4],tensorSize)
    TM2 = np.reshape(OUTPUT[:,5],tensorSize)

    return TE0,TE1,TE2,TM0,TM1,TM2

def straightWaveguide_S(wavelength,width,thickness,gap,length):

    TE0,TE1,TE2,TM0,TM1,TM2 = straightWaveguide(wavelength,width,thickness)

    neff = TE0

    N = wavelength.shape[0]
    S = np.zeros((N,2,2),dtype='complex128')
    S[:,0,1] = np.exp(1j*2*np.pi*radius*neff*angle/wavelength)
    S[:,1,0] = np.exp(1j*2*np.pi*radius*neff*angle/wavelength)
    return S

# ---------------------------------------------------------------------------- #
# Bent waveguide
# ---------------------------------------------------------------------------- #
'''
bentWaveguide()

Calculates the analytic scattering matrix of a simple, parallel waveguide
directional coupler using the ANN.

INPUTS:
wavelength .............. [np array](N,) wavelength points to evaluate
gap ..................... [scalar] gap in the coupler region in microns
width ................... [scalar] width of the waveguides in microns
thickness ............... [scalar] thickness of the waveguides in microns
length .................. [scalar] length of the waveguide in microns

OUTPUTS:
S ....................... [np array](N,2,2) Scattering matrix

'''
def bentWaveguide(wavelength,radius,width,thickness,gap,angle):

    # Pull effective indices from ANN
    neff = 2.323

    N = wavelength.shape[0]
    S = np.zeros((N,2,2),dtype='complex128')
    S[:,0,1] = np.exp(1j*2*np.pi*radius*neff*angle/wavelength)
    S[:,1,0] = np.exp(1j*2*np.pi*radius*neff*angle/wavelength)
    return S
# ---------------------------------------------------------------------------- #
# Evanescent waveguide coupler
# ---------------------------------------------------------------------------- #
'''
evWGcoupler()

Calculates the analytic scattering matrix of a simple, parallel waveguide
directional coupler using the ANN.

INPUTS:
wavelength .............. [np array](N,) wavelength points to evaluate
couplerLength ........... [scalar] length of the coupling region in microns
gap ..................... [scalar] gap in the coupler region in microns
width ................... [scalar] width of the waveguides in microns
thickness ............... [scalar] thickness of the waveguides in microns

OUTPUTS:
S ....................... [np array](N,4,4) Scattering matrix

'''

def evWGcoupler(wavelength,width,thickness,gap,couplerLength):

    neff = 2

    N = wavelength.shape[0]

    # Get the fundamental mode of the waveguide itself
    n0 = 2.323
    # Get the first fundamental mode of the coupler region
    n1 = 2.378022
    # Get the second fundamental mode of the coupler region
    n2 = 2.317864
    # Find the modal differences
    dn = n1 - n2

    # -------- Formulate the S matrix ------------ #
    x =  np.exp(-1j*2*np.pi*n0*couplerLength/wavelength) * np.cos(np.pi*dn/wavelength*couplerLength)
    y =  1j * np.exp(-1j*2*np.pi*n0*couplerLength/wavelength) * np.sin(np.pi*dn/wavelength*couplerLength)

    S = np.zeros((N,4,4),dtype='complex128')

    # Row 1
    S[:,0,1] = x
    S[:,0,3] = y
    # Row 2
    S[:,1,0] = x
    S[:,1,2] = y
    # Row 3
    S[:,2,1] = y
    S[:,2,3] = x
    # Row 4
    S[:,3,0] = y
    S[:,3,2] = x
    return S

# ---------------------------------------------------------------------------- #
# Racetrack Ring Resonator
# ---------------------------------------------------------------------------- #

'''
racetrackRR()

This particular transfer function assumes that the coupling sides of the ring
resonator are straight, and the other two sides are curved. Therefore, the
roundtrip length of the RR is 2*pi*radius + 2*couplerLength.

We assume that the round parts of the ring have negligble coupling compared to
the straight sections.

INPUTS:
wavelength .............. [np array](N,) wavelength points to evaluate
radius .................. [scalar] radius of the sides in microns
couplerLength ........... [scalar] length of the coupling region in microns
gap ..................... [scalar] gap in the coupler region in microns
width ................... [scalar] width of the waveguides in microns
thickness ............... [scalar] thickness of the waveguides in microns

OUTPUTS:
S ....................... [np array](N,4,4) Scattering matrix

'''
def racetrackRR(wavelength,radius=5,couplerLength=5,gap=0.2,width=0.5,thickness=0.2):

    # Sanitize the input
    wavelength = np.squeeze(wavelength)
    N          = wavelength.shape[0]

    # Calculate coupling scattering matrix
    couplerS = evWGcoupler(wavelength,width,thickness,gap,couplerLength)

    # Calculate bent scattering matrix
    bentS = bentWaveguide(wavelength,radius,width,thickness,gap,np.pi)

    # Cascade first bent waveguid
    S = rf.connect_s(couplerS, 2, bentS, 0)

    # Cascade second bent waveguide
    S = rf.connect_s(S, 3, bentS, 0)

    # Cascade final coupler
    S = rf.connect_s(S, 2, couplerS, 0)

    S = rf.innerconnect_s(S, 2,3)

    # Output final s matrix
    return S

# ---------------------------------------------------------------------------- #
# Rectangular Ring Resonator
# ---------------------------------------------------------------------------- #

'''
This particular transfer function assumes that all four sides of the ring
resonator are straight and that the corners are rounded. Therefore, the
roundtrip length of the RR is 2*pi*radius + 2*couplerLength + 2*sideLength.

We assume that the round parts of the ring have negligble coupling compared to
the straight sections.

INPUTS:
wavelength .............. [np array](N,) wavelength points to evaluate
radius .................. [scalar] radius of the sides in microns
couplerLength ........... [scalar] length of the coupling region in microns
sideLength .............. [scalar] length of each side not coupling in microns
gap ..................... [scalar] gap in the coupler region in microns
width ................... [scalar] width of the waveguides in microns
thickness ............... [scalar] thickness of the waveguides in microns

OUTPUTS:
S ....................... [np array](N,4,4) Scattering matrix

'''
def rectangularRR(wavelength,radius=5,couplerLength=5,sideLength=5,
            gap=0.2,width=0.5,thickness=0.2):

    # Sanitize the input

    # Calculate transfer function output

    #
    return