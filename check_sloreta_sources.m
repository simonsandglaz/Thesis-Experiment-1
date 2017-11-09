function check_sloreta_sources()

baseline_eeglab = eeg_load_xdf('./EEG Recordings/baseline_1.xdf');

% meditation_eeglab = eeg_load_xdf('./EEG Recordings/meditation_1.xdf');

baseline_data = eeglab2fieldtrip(baseline_eeglab, 'preprocessing', 'none');

% meditation_data = eeglab2fieldtrip(baseline_eeglab, 'preprocessing', 'none');

% Strip stimulus channel from OpenVibe
cfg = [];
cfg.channel          = {'P4', 'C4', 'T6', 'CP2', 'FC2', 'POz', 'Pz', 'PO4', 'FC1', 'PO3', 'Cz', 'Oz', 'T5', 'P3', 'C3', 'CP1'};
baseline_data = ft_selectdata(cfg, baseline_data)

% Define a custom trail function to stop when I get the baseline-stop event

% cfg = [];
% cfg.dataset            = baseline_data;
% cfg.trialdef.eventtype = 'baseline_start';
% cfg.trialdef.poststim  = 7;
% baseline_data          = ft_definetrial(cfg);


% Preprocessing
cfg = [];
cfg.demean                  = 'yes';     % apply baselinecorrection
cfg.reref 					= 'yes';
cfg.refchannel				= 'all';
% cfg.lpfilter                = 'yes';     % apply lowpass filter
% cfg.lpfreq                  = 58;        % lowpass at 55 Hz
% cfg.hpfilter = 'yes';
% cfg.hpfreq = 1;
cfg.bpfilter = 'yes';
cfg.bpfreq = [1 59]
baseline_trial_data = ft_preprocessing(cfg, baseline_data);

% Clean up some artifacts
cfg.artfctdef.reject  = 'complete';
baseline_clean_data = ft_rejectartifact(cfg, baseline_trial_data);

% Do a fequency analysis to check on things
% cfg        = [];
% cfg.output       = 'pow'; 
% cfg.channel      = 'all';
% cfg.method       = 'mtmconvol';
% cfg.toi = 'all';
% cfg.foi          = 1:40;
% cfg.t_ftimwin    = ones(size(cfg.foi)) * 0.5;
% cfg.tapsmofrq = 2;
% freq       = ft_freqanalysis(cfg, baseline_clean_data);

% cfg = [];
% cfg.showlabels   = 'yes';	
% cfg.layout       = 'biosemi64.lay';
 
% figure;
% ft_multiplotTFR(cfg, freq);


% Create timelock analysis for lcmv beamforming later
cfg                  = [];
cfg.covariance       = 'yes';
cfg.covariancewindow = 'all';
cfg.vartrllength     = 2;
baseline_timelock    = ft_timelockanalysis(cfg, baseline_clean_data);

plot(baseline_timelock.time, baseline_timelock.avg)

% cfg = [];                            
% cfg.layout = 'biosemi64.lay';            
% figure; ft_topoplotER(cfg, baseline_timelock); colorbar;


% compute_models(baseline_timelock)

load leadfield
load sourcemodel
load headmodel
load mri
elec = ft_read_sens('standard_1020.elc');

% create spatial filter using the lcmv beamformer
cfg = [];
cfg.elec  			= elec;
cfg.method          = 'lcmv';
cfg.grid            = leadfield;
cfg.headmodel       = headmodel;
cfg.senstype        = 'eeg';
cfg.channel          = {'P4', 'C4', 'T6', 'CP2', 'FC2', 'POz', 'Pz', 'PO4', 'FC1', 'PO3', 'Cz', 'Oz', 'T5', 'P3', 'C3', 'CP1'};
cfg.lcmv.keepfilter = 'yes';
% cfg.lcmv.fixedori   = 'yes'; % project on axis of most variance using SVD
sourceavg 			= ft_sourceanalysis(cfg, baseline_timelock);

sourceavg.pos = sourcemodel.pos
sourceavg.dim = sourcemodel.dim

% save sourceavg sourceavg;
cfg = [];
cfg.parameter = 'avg.pow';
cfg.interpmethod = 'nearest';
source_interpolated = ft_sourceinterpolate(cfg, sourceavg, mri)

cfg               = [];
cfg.method        = 'slice';
cfg.funparameter  = 'avg.pow';
cfg.maskparameter = cfg.funparameter;
cfg.funcolorlim   = [0.0 1.2];
cfg.opacitylim    = [0.0 1.2]; 
cfg.opacitymap    = 'rampup';
ft_sourceplot(cfg, source_interpolated);

end

function compute_models(baseline_timelock)

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
cfg                 = [];
cfg.headmodel       = headmodel;
cfg.elec			= elec;
cfg.grid.resolution = 10; % use a 3-D grid with a 1 cm resolution
cfg.grid.unit       = 'mm';
% cfg.inwardshift     = -1.5; % I don't think this is neecssary?
sourcemodel         = ft_prepare_sourcemodel(cfg);

save sourcemodel sourcemodel;

% The next step is to discretize the brain volume into a grid.
% For each grid point the lead field matrix is calculated.
% It is calculated with respect to a grid with a 1 cm resolution.
% Create leadfield grid
cfg                  = [];
cfg.elec             = elec;  % electrode distances
cfg.headmodel        = headmodel;   % volume conduction headmodel
cfg.grid             = sourcemodel;  % normalized grid positions
cfg.channel          = {'P4', 'C4', 'T6', 'CP2', 'FC2', 'POz', 'Pz', 'PO4', 'FC1', 'PO3', 'Cz', 'Oz', 'T5', 'P3', 'C3', 'CP1'};
cfg.normalize        = 'yes'; % to remove depth bias (Q in eq. 27 of van Veen et al, 1997)
leadfield            = ft_prepare_leadfield(cfg);

save leadfield leadfield;
end