"""
The data-file handling functions

Author: Matthew Turk <matthewturk@gmail.com>
Author: J. S. Oishi <jsoishi@gmail.com>
Affiliation: KIPAC/SLAC/Stanford
Homepage: http://yt-project.org/
License:
  Copyright (C) 2007-2011 Matthew Turk.  All Rights Reserved.

  This file is part of yt.

  yt is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import h5py
import re
import numpy as np

from yt.utilities.io_handler import \
           BaseIOHandler

class IOHandlerChomboHDF5(BaseIOHandler):
    _data_style = "chombo_hdf5"
    _offset_string = 'data:offsets=0'
    _data_string = 'data:datatype=0'

    def _field_dict(self,fhandle):
        ncomp = int(fhandle['/'].attrs['num_components'])
        temp =  fhandle['/'].attrs.items()[-ncomp:]
        val, keys = zip(*temp)
        val = [int(re.match('component_(\d+)',v).groups()[0]) for v in val]
        return dict(zip(keys,val))
        
    def _read_field_names(self,grid):
        fhandle = h5py.File(grid.filename,'r')
        ncomp = int(fhandle['/'].attrs['num_components'])

        fns = [c[1] for c in f['/'].attrs.items()[-ncomp-1:-1]]
        fhandle.close()
    
    def _read_data_set(self,grid,field):
        # try to read from backup file first
        try:
            backup_filename = grid.pf.backup_filename
            fhandle = h5py.File(backup_filename, 'r')
            g = fhandle["data"]
            grid_group = g["grid_%010i" % grid.id]
            data = grid_group[field][:]
            fhandle.close()
            return data
        except:
            fhandle = h5py.File(grid.hierarchy.hierarchy_filename,'r')

            field_dict = self._field_dict(fhandle)
            lstring = 'level_%i' % grid.Level
            lev = fhandle[lstring]
            dims = grid.ActiveDimensions
            boxsize = dims.prod()
        
            grid_offset = lev[self._offset_string][grid._level_id]
            start = grid_offset+field_dict[field]*boxsize
            stop = start + boxsize
            data = lev[self._data_string][start:stop]

            fhandle.close()
        return data.reshape(dims, order='F')

    def _read_data_slice(self, grid, field, axis, coord):
        sl = [slice(None), slice(None), slice(None)]
        sl[axis] = slice(coord, coord + 1)
        return self._read_data_set(grid,field)[sl]

    def _read_particles(self, grid, field):
        """
        parses the Orion Star Particle text files
             
        """
        index = {'particle_mass': 0,
                 'particle_position_x': 1,
                 'particle_position_y': 2,
                 'particle_position_z': 3,
                 'particle_momentum_x': 4,
                 'particle_momentum_y': 5,
                 'particle_momentum_z': 6,
                 'particle_angmomen_x': 7,
                 'particle_angmomen_y': 8,
                 'particle_angmomen_z': 9,
                 'particle_mlast': 10,
                 'particle_mdeut': 11,
                 'particle_n': 12,
                 'particle_mdot': 13,
                 'particle_burnstate': 14,
                 'particle_id': 15}

        def read(line, field):
            return float(line.split(' ')[index[field]])

        fn = grid.pf.fullplotdir[:-4] + "sink"
        with open(fn, 'r') as f:
            lines = f.readlines()
            particles = []
            for line in lines[1:]:
                if grid.NumberOfParticles > 0:
                    coord = read(line, "particle_position_x"), \
                            read(line, "particle_position_y"), \
                            read(line, "particle_position_z")
                    if ( (grid.LeftEdge < coord).all() and
                         (coord <= grid.RightEdge).all() ):
                        particles.append(read(line, field))
        return np.array(particles)
