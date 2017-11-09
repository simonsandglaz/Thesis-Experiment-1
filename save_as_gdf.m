% Demostration for generating EDF/BDF/GDF-files
% DEMO3 is part of the biosig-toolbox
%    and it tests also Matlab/Octave for its correctness. 
% 

%	Copyright (C) 2000-2005,2006,2007,2008,2011,2013 by Alois Schloegl <alois.schloegl@gmail.com>
%    	This is part of the BIOSIG-toolbox http://biosig.sf.net/
%
%    BioSig is free software: you can redistribute it and/or modify
%    it under the terms of the GNU General Public License as published by
%    the Free Software Foundation, either version 3 of the License, or
%    (at your option) any later version.
%
%    BioSig is distributed in the hope that it will be useful,
%    but WITHOUT ANY WARRANTY; without even the implied warranty of
%    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
%    GNU General Public License for more details.
%
%    You should have received a copy of the GNU General Public License
%    along with BioSig.  If not, see <http://www.gnu.org/licenses/>.

clear HDR;

VER   = version;
cname = computer;

% select file format 
HDR.TYPE='GDF';  

% set Filename
HDR.FileName = ['TEST_',VER([1,3]),cname(1:3),'_e1.',HDR.TYPE];

% recording time [YYYY MM DD hh mm ss.ccc]
HDR.T0 = clock;	

% number of channels
HDR.NS = 6;

% Duration of one block in seconds
HDR.SampleRate = 125;
HDR.SPR = 600;
HDR.Dur = HDR.SPR/HDR.SampleRate;

% channel identification, max 80 char. per channel
HDR.Label={'chan 1  ';'chan 2  ';'chan 3  ';'chan 4  ';'chan 5  ';'NEQS    '};

% Transducer, mx 80 char per channel
HDR.Transducer = {'';'';'';'';'';''};

% define datatypes (GDF only, see GDFDATATYPE.M for more details)
HDR.GDFTYP = 5*ones(1,HDR.NS);

% define scaling factors 
HDR.PhysMax = [100;100;100;100;100;100];
HDR.PhysMin = [0;0;0;0;0;0];
HDR.DigMax  = repmat(2^15-1,size(HDR.PhysMax));
HDR.DigMin  = repmat(1-2^15,size(HDR.PhysMax));
HDR.FLAG.UCAL = 1; 	% data x is already converted to internal (usually integer) values (no rescaling within swrite);
% define sampling delay between channels  
HDR.TOffset = [0:5]*1e-6;

% define physical dimension
HDR.PhysDim = {'uV';'mV';'%';'Ohm';'-';'°C'};	%% must be encoded in unicode (UTF8)
HDR.Impedance = [5000,50000,NaN,NaN,NaN,NaN];         % electrode impedance (in Ohm) for voltage channels 
HDR.fZ = [NaN,NaN,NaN,400000,NaN,NaN];                % probe frequency in Hz for Impedance channel

t = [100:100:size(x,1)]';
HDR.NRec = 1;
HDR.VERSION = 2.20;  
HDR.EVENT.POS = t;
HDR.EVENT.TYP = t/100;

if 0, %try,
	mexSSAVE(HDR,x);
else %catch
	HDR1 = sopen(HDR,'w');
	HDR1 = swrite(HDR1,x);
	HDR1 = sclose(HDR1);
end;

%
[s0,HDR0] = sload(HDR.FileName);	% test file 

HDR0=sopen(HDR0.FileName,'r');
[s0,HDR0]=sread(HDR0);
HDR0=sclose(HDR0); 

%plot(s0-x)


