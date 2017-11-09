function neurofeedback_main()

% Record some baseline data
cfg                = [];
cfg.blocksize      = 1;                            % seconds
cfg.dataset        = 'buffer://localhost:1972';    % where to read the data
cfg.buffer         = 'last';
neurofeedback_baseline(cfg);

load baseline_data

% Preprocessing
cfg = [];
cfg.demean                  = 'yes';     % apply baselinecorrection
cfg.reref 									= 'yes';
cfg.refchannel							= 'all';
% cfg.bpfilter 								= 'yes'; % apply a bandpass filter for 40-57hz
% cfg.bpfreq									= [40 55];
% cfg.bsfilter 								= 'yes'; % apply a bandstop filter for 58-62hz
% cfg.bsfreq									= [58 62];

cfg.lpfilter                = 'yes';     % apply lowpass filter
cfg.lpfreq                  = 55;        % lowpass at 55 Hz
trial_data = ft_preprocessing(cfg, baseline_data);  

% Clean up some artifacts
cfg.artfctdef.reject  = 'complete';
clean_data = ft_rejectartifact(cfg, trial_data);

% Create timelock analysis for lcmv beamforming later
cfg                  = [];
cfg.covariance       = 'yes';
cfg.covariancewindow = 'all';
cfg.vartrllength     = 2;
timelock             = ft_timelockanalysis(cfg, clean_data);

load mri
load segmentedmri
load headmodel

elec = ft_read_sens('standard_1020.elc');   

% Now prepare the source model. %
% Here one has the option to make a 'normalized grid', such that the grid points in different subjects are aligned in MNI-space. %
% create the subject specific grid
hdr                 = baseline_data.hdr;
cfg                 = [];
cfg.elec						= elec;
cfg.headmodel       = headmodel;
cfg.lcmv.reducerank = 3; % default for MEG is 2, for EEG is 3
cfg.grid.resolution = 1; % use a 3-D grid with a 1 cm resolution
cfg.grid.unit       = 'mm';
% cfg.inwardshift     = -1.5; % I don't think this is neecssary?
sourcemodel         = ft_prepare_sourcemodel(cfg);

% The next step is to discretize the brain volume into a grid.
% For each grid point the lead field matrix is calculated.
% It is calculated with respect to a grid with a 1 cm resolution.
% Create leadfield grid
cfg                  = [];
cfg.elec             = elec;  % electrode distances
cfg.headmodel        = headmodel;   % volume conduction headmodel
cfg.grid             = sourcemodel;  % normalized grid positions
cfg.grid.pos         = [-6 -60 18];
cfg.grid.inside	  	 = [true];
cfg.channel          = {'O1', 'T5', 'Oz', 'P3', 'Pz', 'P4', 'T6', 'O2'};
cfg.normalize        = 'yes'; % to remove depth bias (Q in eq. 27 of van Veen et al, 1997)
leadfield            = ft_prepare_leadfield(cfg);

save leadfield leadfield;

% create spatial filter using the lcmv beamformer
% FINALLY THERE! Linearly Constrained Minimum Variance !!!!
cfg = [];
cfg.elec  					= elec;
cfg.method          = 'lcmv';
cfg.grid            = leadfield;
% cfg.grid.pos        = [-6 -60 18];
% cfg.grid.inside		  = [true];
% cfg.grid.unit    		= sourcemodel.unit;
cfg.headmodel       = headmodel;
cfg.channel         = {'O1', 'T5', 'Oz', 'P3', 'Pz', 'P4', 'T6', 'O2'};
cfg.senstype        = 'eeg';
cfg.lcmv.keepfilter = 'yes';
% cfg.lcmv.reducerank = 1;
cfg.lcmv.fixedori   = 'yes'; % project on axis of most variance using SVD
sourceavg 	= ft_sourceanalysis(cfg, timelock);

save sourceavg sourceavg;

beamformer_pcc_filter = sourceavg.avg.filter{1};

% create spatial filter using the lcmv beamformer
% FINALLY THERE! Linearly Constrained Minimum Variance !!!!
cfg = [];
cfg.elec            = elec;
cfg.method          = 'lcmv';
cfg.grid            = leadfield;
% cfg.grid.pos        = [-6 -60 18];
% cfg.grid.inside     = [true];
% cfg.grid.unit       = sourcemodel.unit;
cfg.headmodel       = headmodel;
cfg.channel         = {'O1', 'T5', 'Oz', 'P3', 'Pz', 'P4', 'T6', 'O2'};
cfg.senstype        = 'eeg';
cfg.lcmv.keepfilter = 'yes';
% cfg.lcmv.reducerank = 1;
% cfg.lcmv.fixedori   = 'yes'; % project on axis of most variance using SVD
sourceavg_xyz   = ft_sourceanalysis(cfg, timelock);

beamformer_pcc_filter_xyz = sourceavg_xyz.avg.filter{1};


% cfg              = [];
% cfg.funparameter = 'gray';
% ft_sourceplot(cfg,segmentedmri);

figure
hold on
ft_plot_mesh(sourcemodel.pos(sourcemodel.inside,:));
camlight
ft_plot_sens(elec);


disp(beamformer_pcc_filter);
save_fixed_origin_spatial_filter(trial_data, beamformer_pcc_filter);
save_spatial_filter(trial_data, beamformer_pcc_filter_xyz);

end

function save_fixed_origin_spatial_filter(trial_data, spatial_filter)
pcc_data = [];
pcc_data.label = {'PCC'};
pcc_data.time = trial_data.time;

chansel = ft_channelselection('eeg', trial_data.label); % find EEG sensor names
chansel = match_str(trial_data.label, chansel);         % find EEG sensor indices

for i=1:length(trial_data.trial)
  pcc_data.trial{i} = spatial_filter * trial_data.trial{i}(chansel,:);
end

pcc_mean = mean(pcc_data.trial{1});
pcc_std = std(pcc_data.trial{1});

% Make Spatial Filter OpenViBE settings
docNode = com.mathworks.xml.XMLUtils.createDocument... 
    ('OpenViBE-SettingsOverride');
docRootNode = docNode.getDocumentElement;
% Spatial Filter
thisElement = docNode.createElement('SettingValue');

thisElement.appendChild... 
        (docNode.createTextNode(sprintf('%f;%f;%f;%f;%f;%f;%f;%f;', ...
          spatial_filter(1), ...
          spatial_filter(2), ...
          spatial_filter(3), ... 
          spatial_filter(4), ...
          spatial_filter(5), ...
          spatial_filter(6), ...
          spatial_filter(7), ...
          spatial_filter(8))));
docRootNode.appendChild(thisElement);
% Output Channels
thisElement = docNode.createElement('SettingValue');
thisElement.appendChild(docNode.createTextNode('1'));
docRootNode.appendChild(thisElement);
% Input Channels
thisElement = docNode.createElement('SettingValue');
thisElement.appendChild(docNode.createTextNode('8'));
docRootNode.appendChild(thisElement);
% Nothing
thisElement = docNode.createElement('SettingValue');
docRootNode.appendChild(thisElement);

xmlFileName = ['spatial_filter',''];
xmlwrite(xmlFileName,docNode);

% Make DSP for OpenViBE
docNode = com.mathworks.xml.XMLUtils.createDocument... 
    ('OpenViBE-SettingsOverride');
docRootNode = docNode.getDocumentElement;
% Output Channels
thisElement = docNode.createElement('SettingValue');
thisElement.appendChild(docNode.createTextNode(sprintf('(x - %f)/%f', pcc_mean, pcc_std)));
docRootNode.appendChild(thisElement);

xmlFileName = ['dsp',''];
xmlwrite(xmlFileName,docNode);

end

function save_spatial_filter(trial_data, spatial_filter)
pcc_data = [];
pcc_data.label = {'PCC'};
pcc_data.time = trial_data.time;

pcc_data_x = [];
pcc_data_y = [];
pcc_data_z = [];

pcc_data_x.label = {'PCC_X'};
pcc_data_y.label = {'PCC_Y'};
pcc_data_z.label = {'PCC_Z'};

pcc_data_x.time = trial_data.time;
pcc_data_y.time = trial_data.time;
pcc_data_z.time = trial_data.time;

chansel = ft_channelselection('eeg', trial_data.label); % find EEG sensor names
chansel = match_str(trial_data.label, chansel);         % find EEG sensor indices

for i=1:length(trial_data.trial)
  pcc_data_x.trial{i} = spatial_filter(1,:) * trial_data.trial{i}(chansel,:);
  pcc_data_y.trial{i} = spatial_filter(2,:) * trial_data.trial{i}(chansel,:);
  pcc_data_z.trial{i} = spatial_filter(3,:) * trial_data.trial{i}(chansel,:);
end

pcc_mean_x = mean(pcc_data_x.trial{1});
pcc_mean_y = mean(pcc_data_y.trial{1});
pcc_mean_z = mean(pcc_data_z.trial{1});

pcc_std_x = std(pcc_data_x.trial{1});
pcc_std_y = std(pcc_data_y.trial{1});
pcc_std_z = std(pcc_data_z.trial{1});

fprintf('X Mean: %f, X STD: %f', pcc_mean_x, pcc_std_x)
fprintf('Y Mean: %f, Y STD: %f', pcc_mean_y, pcc_std_y)
fprintf('Z Mean: %f, Z STD: %f', pcc_mean_z, pcc_std_z)

% fileID = fopen('means.txt','w');
% fprintf(fileID,'%f', pcc_mean);
% fprintf(fileID,'%f',pcc_std);
% fclose(fileID);


% Make Spatial Filter OpenViBE settings
docNode = com.mathworks.xml.XMLUtils.createDocument... 
    ('OpenViBE-SettingsOverride');
docRootNode = docNode.getDocumentElement;
% Spatial Filter
thisElement = docNode.createElement('SettingValue');

spatial_filter_string = '';
beamformer_pcc_filter = spatial_filter';
for i = 1:numel(beamformer_pcc_filter)
  spatial_filter_string = strcat(spatial_filter_string, sprintf('%f;', beamformer_pcc_filter(i)));
end


thisElement.appendChild...
  (docNode.createTextNode(spatial_filter_string));
docRootNode.appendChild(thisElement);

% Output Channels
thisElement = docNode.createElement('SettingValue');
thisElement.appendChild(docNode.createTextNode('3'));
docRootNode.appendChild(thisElement);
% Input Channels
thisElement = docNode.createElement('SettingValue');
thisElement.appendChild(docNode.createTextNode('8'));
docRootNode.appendChild(thisElement);
% Nothing
thisElement = docNode.createElement('SettingValue');
docRootNode.appendChild(thisElement);

xmlFileName = ['spatial_filter_xyz',''];
xmlwrite(xmlFileName,docNode);

% % Make DSP for OpenViBE
% docNode = com.mathworks.xml.XMLUtils.createDocument... 
%     ('OpenViBE-SettingsOverride');
% docRootNode = docNode.getDocumentElement;
% % Output Channels
% thisElement = docNode.createElement('SettingValue');
% thisElement.appendChild(docNode.createTextNode(sprintf('(x - %f)/%f', pcc_mean, pcc_std)));
% docRootNode.appendChild(thisElement);

% xmlFileName = ['dsp_xyz',''];
% xmlwrite(xmlFileName,docNode);
end