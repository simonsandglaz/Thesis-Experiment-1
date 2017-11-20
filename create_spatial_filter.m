function create_spatial_filter(subject_id, set, run)

baseline_location = sprintf('./experiment_data/subject_%d/set_%d/run_%d/baseline/eeg.edf', subject_id, set, run)
% baseline_eeglab = readedf('./TEST_1.edf')
% baseline_eeglab = readedf(baseline_location)

% baseline_eeglab = eeg_load_xdf('./EEG Recordings/baseline_1.xdf');

% meditation_eeglab = eeg_load_xdf('./EEG Recordings/meditation_1.xdf');

% baseline_data = eeglab2fieldtrip(baseline_eeglab, 'preprocessing', 'none');

% meditation_data = eeglab2fieldtrip(baseline_eeglab, 'preprocessing', 'none');

% Define Trials
cfg            = [];
cfg.dataset    = baseline_location;
cfg.continuous = 'yes';
cfg.channel    = 'all';
baseline_data           = ft_preprocessing(cfg);

% Preprocessing
cfg = [];
cfg.demean                  = 'yes';     % apply baselinecorrection
cfg.reref 					= 'yes';
cfg.refchannel				= 'all';

cfg.lpfilter                = 'yes';     % apply lowpass filter
cfg.lpfreq                  = 55;        % lowpass at 55 Hz
baseline_trial_data = ft_preprocessing(cfg, baseline_data);  

% Clean up some artifacts
cfg.artfctdef.reject  = 'complete';
baseline_clean_data = ft_rejectartifact(cfg, baseline_trial_data);

% Create timelock analysis for lcmv beamforming later
cfg                  = [];
cfg.covariance       = 'yes';
cfg.covariancewindow = 'all';
cfg.vartrllength     = 2;
baseline_timelock    = ft_timelockanalysis(cfg, baseline_clean_data);

load mri
load segmentedmri
load headmodel

% cfg=[];
% ft_sourceplot(cfg,mri);

% cfg              = [];
% cfg.funparameter = 'scalp';
% ft_sourceplot(cfg, segmentedmri);

elec = ft_read_sens('standard_1020.elc');

% Plot channels on headmodel
% cfg        = [];
% cfg.shift  = 0.3;
% cfg.unit   = 'mm';
% cfg.method = 'hexahedral';
% mri_mesh = ft_prepare_mesh(cfg, segmentedmri);

% figure
% hold on
% ft_plot_mesh(mri_mesh,'surfaceonly','yes','vertexcolor','none','edgecolor','none','facecolor',[0.5 0.5 0.5],'face alpha',0.7)
% camlight
% ft_plot_sens(elec, 'style', 'sr');


% Now prepare the source model. %
% Here one has the option to make a 'normalized grid', such that the grid points in different subjects are aligned in MNI-space. %
% create the subject specific grid
% hdr                 = baseline_data.hdr;
% cfg                 = [];
% cfg.headmodel       = headmodel;
% cfg.elec			= elec;
% cfg.grid.resolution = 10; % use a 3-D grid with a 1 cm resolution
% cfg.grid.unit       = 'mm';
% % cfg.inwardshift     = -1.5; % I don't think this is neecssary?
% sourcemodel         = ft_prepare_sourcemodel(cfg);

% save sourcemodel sourcemodel;
load sourcemodel
% The next step is to discretize the brain volume into a grid.
% For each grid point the lead field matrix is calculated.
% It is calculated with respect to a grid with a 1 cm resolution.
% Create leadfield grid
% cfg                  = [];
% cfg.elec             = elec;  % electrode distances
% cfg.headmodel        = headmodel;   % volume conduction headmodel
% cfg.grid             = sourcemodel;  % normalized grid positions
% % cfg.channel          = {'Fpz', 'Fp1', 'AF3', 'FC1', 'Fz', 'FC2', 'AF4', 'PO4', 'Fp2', 'Oz', 'P4', 'CP2', 'Pz', 'CP1', 'P3', 'PO3'};
% cfg.normalize        = 'yes'; % to remove depth bias (Q in eq. 27 of van Veen et al, 1997)
% leadfield            = ft_prepare_leadfield(cfg);

% save leadfield leadfield
load leadfield

% create spatial filter using the lcmv beamformer
cfg = [];
cfg.elec  			= elec;
cfg.method          = 'lcmv';
cfg.grid            = leadfield;
% cfg.grid.pos        = [-6 -60 18];
% cfg.grid.inside		= [true];
cfg.grid.unit    	= sourcemodel.unit;
cfg.headmodel       = headmodel;
cfg.senstype        = 'eeg';
cfg.channel          = {'Fpz', 'Fp1', 'AF3', 'FC1', 'Fz', 'FC2', 'AF4', 'PO4', 'Fp2', 'Oz', 'P4', 'CP2', 'Pz', 'CP1', 'P3', 'PO3'};
cfg.lcmv.keepfilter = 'yes';
% cfg.lcmv.fixedori   = 'yes'; % project on axis of most variance using SVD
sourceavg 			= ft_sourceanalysis(cfg, baseline_timelock);

sourceavg.pos = sourcemodel.pos
sourceavg.dim = sourcemodel.dim

% cfg              = [];
% cfg.voxelcoord   = 'no';
% cfg.parameter    = 'pow';
% cfg.interpmethod = 'nearest';
% source_int  = ft_sourceinterpolate(cfg, sourceavg, segmentedmri);

cfg              = [];
cfg.parameter    = 'avg.pow';
cfg.interpmethod = 'nearest';
source_int  = ft_sourceinterpolate(cfg, sourceavg, segmentedmri);

cfg               = [];
cfg.method        = 'slice';
cfg.funparameter  = 'avg.pow';
cfg.maskparameter = cfg.funparameter;
cfg.funcolorlim   = [0.0 1.2];
cfg.opacitylim    = [0.0 1.2]; 
cfg.opacitymap    = 'rampup';  
ft_sourceplot(cfg, source_int);

% cfg               = [];
% cfg.method        = 'ortho';
% cfg.funparameter  = 'stat';
% % cfg.maskparameter = 'mask';
% cfg.location = [-6 -60 18];
% cfg.funcolormap = 'jet';
% ft_sourceplot(cfg, source_int);

% save sourceavg sourceavg;
% cfg = [];
% cfg.parameter = 'avg.pow';
% cfg.interpmethod = 'nearest';
% source_interpolated = ft_sourceinterpolate(cfg, sourceavg, mri)

% cfg               = [];
% cfg.method        = 'slice';
% cfg.funparameter  = 'avg.pow';
% cfg.maskparameter = cfg.funparameter;
% cfg.funcolorlim   = [0.0 1.2];
% cfg.opacitylim    = [0.0 1.2]; 
% cfg.opacitymap    = 'rampup';
% ft_sourceplot(cfg, source_interpolated);

% save sourceavg sourceavg;

% beamformer_pcc_filter = sourceavg.avg.filter{1};

% % create spatial filter using the lcmv beamformer
% % FINALLY THERE! Linearly Constrained Minimum Variance !!!!
% cfg = [];
% cfg.method          = 'lcmv';
% cfg.grid            = leadfield;
% cfg.grid.pos        = [-6 -60 18];
% cfg.grid.inside     = [true];
% cfg.grid.unit       = sourcemodel.unit;
% cfg.headmodel       = headmodel;
% cfg.senstype        = 'eeg';
% cfg.lcmv.keepfilter = 'yes';
% % cfg.lcmv.reducerank = 1;
% % cfg.lcmv.fixedori   = 'yes'; % project on axis of most variance using SVD
% sourceavg_xyz   = ft_sourceanalysis(cfg, timelock);

% beamformer_pcc_filter_xyz = sourceavg_xyz.avg.filter{1};


% cfg              = [];
% cfg.funparameter = 'gray';
% ft_sourceplot(cfg,segmentedmri);

% figure
% hold on
% ft_plot_mesh(sourcemodel.pos(sourcemodel.inside,:));
% camlight
% ft_plot_sens(elec);


% disp(beamformer_pcc_filter);
end
