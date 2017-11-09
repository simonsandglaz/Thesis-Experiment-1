function prepare_headmodel()
% Load MRI

load './headmodel/standard_seg.mat'
segmentedmri = mri;
save segmentedmri segmentedmri;

load './headmodel/standard_mri.mat'
% mri = ft_read_mri('headmodel/standard_mri.mat');
save mri mri;

load './headmodel/standard_bem.mat'
headmodel = vol;
save headmodel headmodel;

% The first step in the procedure is to construct a forward model.
% The forward model allows us to calculate an estimate of the field measured by 
% the EEG sensors for a given current distribution. In EEG analysis a 
% forward model is typically constructed for each subject, but I am not doing that here.
% There are many types of forward models which to various degrees take the individual anatomy into account. 
% We will here use a semi-realistic head model developed by Nolte (2003). 
% It is based on a correction of the lead field for a spherical volume conductor by a superposition of basis functions, gradients of harmonic functions constructed from spherical harmonics.

% The first step in constructing the forward model is to find the brain surface from the subjects MRI.
% This procedure is termed segmentation. Note that segmentation is quite time consuming. 
% Since we have the segmented MRI, we cann just load that.

% Segment the MRI
% cfg          = [];
% segmentedmri = ft_volumesegment(cfg, mri);
% segmentedmri.transform = mri.transform;
% segmentedmri.anatomy   = mri.anatomy;
% save segmentedmri segmentedmri;


% % will produce a volume with 3 binary masks, representing the brain surface, scalp surface, and skull which do not overlap.
% % cfg              = [];
% % cfg.output = {'brain' 'scalp' 'skull'};
% % segmentedmri_bsc  = ft_volumesegment(cfg, segmentedmri);
% % segmentedmri.transform = mri.transform;
% % segmentedmri.anatomy   = mri.anatomy;
% % save segmentedmri_bsc segmentedmri_bsc;

% cfg              = [];
% cfg.funparameter = 'scalp';
% ft_sourceplot(cfg, segmentedmri);

% % Prepare a mesh of the MRI for visualizations
% cfg        = [];
% cfg.shift  = 0.3;
% cfg.method = 'hexahedral';
% mri_mesh = ft_prepare_mesh(cfg,segmentedmri);
% save mri_mesh mri_mesh

% % % Finally prepare the headmodel
% cfg = [];
% cfg.method = 'openmeeg';
% headmodel = ft_prepare_headmodel(cfg, segmentedmri);
% save headmodel headmodel;

% cfg              = [];
% cfg.funparameter = 'gray';
% ft_sourceplot(cfg,segmentedmri);

% % Reslice MRI to align it properly, but you lose header info
% cfg = [];
% reslice = ft_volumereslice(cfg, mri);
% save reslice reslice;

% % Segment the resliced MRI
% cfg          = [];
% segmentedmri_resliced = ft_volumesegment(cfg, reslice);
% segmentedmri_resliced.transform = reslice.transform;
% segmentedmri_resliced.anatomy   = reslice.anatomy;
% save segmentedmri_resliced segmentedmri_resliced;

% cfg              = [];
% cfg.funparameter = 'gray';
% ft_sourceplot(cfg,segmentedmri_resliced);

