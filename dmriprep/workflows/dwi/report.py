#!/usr/bin/env python


# def init_dwi_report_wf():
#
#     import nipype.interfaces.freesurfer as fs
#     import nipype.interfaces.fsl as fsl
#     import nipype.interfaces.io as nio
#     import nipype.interfaces.dipy as dipy
#     import nipype.interfaces.utility as niu
#     import nipype.pipeline.engine as pe
#
#     inputspec = pe.Node(niu.IdentityInterface(fields=[
#         'subject_id',
#         'dwi_file',
#         'dwi_file_ap',
#         'dwi_file_pa',
#         'bvec_file',
#         'bval_file',
#         'subjects_dir',
#         'out_dir',
#         'eddy_niter',
#         'slice_outlier_threshold'
#     ]), name="inputspec")
#
#     def id_outliers_fn(outlier_report, threshold, dwi_file):
#         """Get list of scans that exceed threshold for number of outliers
#         Parameters
#         ----------
#         outlier_report: string
#             Path to the fsl_eddy outlier report
#         threshold: int or float
#             If threshold is an int, it is treated as number of allowed outlier
#             slices. If threshold is a float between 0 and 1 (exclusive), it is
#             treated the fraction of allowed outlier slices before we drop the
#             whole volume.
#         dwi_file: string
#             Path to nii dwi file to determine total number of slices
#         Returns
#         -------
#         drop_scans: numpy.ndarray
#             List of scan indices to drop
#         """
#         import nibabel as nib
#         import numpy as np
#         import os.path as op
#         import parse
#
#         with open(op.abspath(outlier_report), 'r') as fp:
#             lines = fp.readlines()
#
#         p = parse.compile(
#             "Slice {slice:d} in scan {scan:d} is an outlier with "
#             "mean {mean_sd:f} standard deviations off, and mean "
#             "squared {mean_sq_sd:f} standard deviations off."
#         )
#
#         outliers = [p.parse(l).named for l in lines]
#         scans = {d['scan'] for d in outliers}
#
#         def num_outliers(scan, outliers):
#             return len([d for d in outliers if d['scan'] == scan])
#
#         if 0 < threshold < 1:
#             img = nib.load(dwi_file)
#             try:
#                 threshold *= img.header.get_n_slices()
#             except nib.spatialimages.HeaderDataError:
#                 print('WARNING. We are not sure which dimension has the '
#                       'slices in this image. So we are using the 3rd dim.', img.shape)
#                 threshold *= img.shape[2]
#
#         drop_scans = np.array([
#             s for s in scans
#             if num_outliers(s, outliers) > threshold
#         ])
#
#         outpath = op.abspath("dropped_scans.txt")
#         np.savetxt(outpath, drop_scans, fmt="%d")
#
#         return drop_scans, outpath
#
#     id_outliers_node = pe.Node(niu.Function(
#         input_names=["outlier_report", "threshold", "dwi_file"],
#         output_names=["drop_scans", "outpath"],
#         function=id_outliers_fn),
#         name="id_outliers_node"
#     )
#
#     wf.connect(inputspec, 'dwi_file', id_outliers_node, 'dwi_file')
#     wf.connect(inputspec, 'slice_outlier_threshold', id_outliers_node, 'threshold')
#
#     wf.connect(prep, "fsl_eddy.out_outlier_report",
#                id_outliers_node, "outlier_report")
#
#     fslroi = pe.Node(fsl.ExtractROI(t_min=0, t_size=1), name="fslroi")
#     wf.connect(prep, "outputnode.out_file", fslroi, "in_file")
#
#     bbreg = pe.Node(fs.BBRegister(contrast_type="t2", init="coreg",
#                                   out_fsl_file=True,
#                                   # subjects_dir=subjects_dir,
#                                   epi_mask=True),
#                     name="bbreg")
#     bbreg.inputs.subject_id = 'freesurfer'  # bids_sub_name
#     wf.connect(fslroi, "roi_file", bbreg, "source_file")
#     wf.connect(inputspec, 'subjects_dir', bbreg, 'subjects_dir')
#
#     def drop_outliers_fn(in_file, in_bval, in_bvec, drop_scans):
#         """Drop outlier volumes from dwi file
#         Parameters
#         ----------
#         in_file: string
#             Path to nii dwi file to drop outlier volumes from
#         in_bval: string
#             Path to bval file to drop outlier volumes from
#         in_bvec: string
#             Path to bvec file to drop outlier volumes from
#         drop_scans: numpy.ndarray
#             List of scan indices to drop
#         Returns
#         -------
#         out_file: string
#             Path to "thinned" output dwi file
#         out_bval: string
#             Path to "thinned" output bval file
#         out_bvec: string
#             Path to "thinned" output bvec file
#         """
#         import nibabel as nib
#         import numpy as np
#         import os.path as op
#         from nipype.utils.filemanip import fname_presuffix
#
#         img = nib.load(op.abspath(in_file))
#         img_data = img.get_data()
#         img_data_thinned = np.delete(img_data,
#                                      drop_scans,
#                                      axis=3)
#         if isinstance(img, nib.nifti1.Nifti1Image):
#             img_thinned = nib.Nifti1Image(img_data_thinned.astype(np.float64),
#                                           img.affine,
#                                           header=img.header)
#         elif isinstance(img, nib.nifti2.Nifti2Image):
#             img_thinned = nib.Nifti2Image(img_data_thinned.astype(np.float64),
#                                           img.affine,
#                                           header=img.header)
#         else:
#             raise TypeError("in_file does not contain Nifti image datatype.")
#
#         out_file = fname_presuffix(in_file, suffix="_thinned", newpath=op.abspath('.'))
#         nib.save(img_thinned, op.abspath(out_file))
#
#         bval = np.loadtxt(in_bval)
#         bval_thinned = np.delete(bval, drop_scans, axis=0)
#         out_bval = fname_presuffix(in_bval, suffix="_thinned", newpath=op.abspath('.'))
#         np.savetxt(out_bval, bval_thinned)
#
#         bvec = np.loadtxt(in_bvec)
#         bvec_thinned = np.delete(bvec, drop_scans, axis=1)
#         out_bvec = fname_presuffix(in_bvec, suffix="_thinned", newpath=op.abspath('.'))
#         np.savetxt(out_bvec, bvec_thinned)
#
#         return out_file, out_bval, out_bvec
#
#     drop_outliers_node = pe.Node(niu.Function(
#         input_names=["in_file", "in_bval", "in_bvec", "drop_scans"],
#         output_names=["out_file", "out_bval", "out_bvec"],
#         function=drop_outliers_fn),
#         name="drop_outliers_node"
#     )
#
#     # Align the output of drop_outliers_node & also the eddy corrected version to the anatomical space
#     # without resampling. and then for aparc+aseg & the mask, resample to the larger voxel size of the B0 image from
#     # fslroi. Also we need to apply the transformation to both bvecs (dropped & eddied) and I think we can just load
#     # the affine from bbreg (sio.loadmat) and np.dot(coord, aff) for each coord in bvec
#
#     def get_orig(subjects_dir, sub='freesurfer'):
#         import os.path as op
#         return op.join(subjects_dir, sub, "mri", "orig.mgz")
#
#     def get_aparc_aseg(subjects_dir, sub='freesurfer'):
#         import os.path as op
#         return op.join(subjects_dir, sub, "mri", "aparc+aseg.mgz")
#
#     # transform the dropped volume version to anat space w/ out resampling
#     voltransform = pe.Node(fs.ApplyVolTransform(no_resample=True),
#                            iterfield=['source_file', 'reg_file'],
#                            name='transform')
#
#     wf.connect(inputspec, 'subjects_dir', voltransform, 'subjects_dir')
#     wf.connect(inputspec, ('subjects_dir', get_aparc_aseg), voltransform, 'target_file')
#     wf.connect(prep, "outputnode.out_file", voltransform, "source_file")
#     wf.connect(bbreg, "out_reg_file", voltransform, "reg_file")
#
#     def apply_transform_to_bvecs_fn(bvec_file, reg_mat_file):
#         import numpy as np
#         import nipype.utils.filemanip as fm
#         import os
#
#         aff = np.loadtxt(reg_mat_file)
#         bvecs = np.loadtxt(bvec_file)
#         bvec_trans = []
#         for bvec in bvecs.T:
#             coord = np.hstack((bvec, [1]))
#             coord_trans = np.dot(coord, aff)[:-1]
#             bvec_trans.append(coord_trans)
#         out_bvec = fm.fname_presuffix(bvec_file, suffix="anat_space", newpath=os.path.abspath('.'))
#         np.savetxt(out_bvec, np.asarray(bvec_trans).T)
#         return out_bvec
#
#     apply_transform_to_bvecs_node = pe.Node(niu.Function(input_names=['bvec_file', 'reg_mat_file'],
#                                                          output_names=['out_bvec'],
#                                                          function=apply_transform_to_bvecs_fn),
#                                             name="applyTransformToBvecs")
#     wf.connect(bbreg, 'out_fsl_file', apply_transform_to_bvecs_node, 'reg_mat_file')
#     wf.connect(prep, 'outputnode.out_bvec', apply_transform_to_bvecs_node, 'bvec_file')
#
#     # ok cool, now lets do the thresholding.
#
#     wf.connect(id_outliers_node, "drop_scans", drop_outliers_node, "drop_scans")
#     wf.connect(voltransform, "transformed_file", drop_outliers_node, "in_file")
#     wf.connect(inputspec, 'bval_file', drop_outliers_node, 'in_bval')
#     wf.connect(apply_transform_to_bvecs_node, "out_bvec", drop_outliers_node, "in_bvec")
#
#     # lets compute the tensor on both the dropped volume scan
#     # and also the original, eddy corrected one.
#     get_tensor = pe.Node(dipy.DTI(), name="dipy_tensor")
#     wf.connect(drop_outliers_node, "out_file", get_tensor, "in_file")
#     wf.connect(drop_outliers_node, "out_bval", get_tensor, "in_bval")
#     wf.connect(drop_outliers_node, "out_bvec", get_tensor, "in_bvec")
#
#     get_tensor_eddy = get_tensor.clone('dipy_tensor_eddy')
#     wf.connect(voltransform, 'transformed_file', get_tensor_eddy, "in_file")
#     wf.connect(apply_transform_to_bvecs_node, 'out_bvec', get_tensor_eddy, "in_bvec")
#     wf.connect(inputspec, 'bval_file', get_tensor_eddy, 'in_bval')
#
#     # AK: What is this, some vestigal node from a previous workflow?
#     # I'm not sure why the tensor gets scaled. but i guess lets scale it for
#     # both the dropped & eddy corrected versions.
#     scale_tensor = pe.Node(name='scale_tensor', interface=fsl.BinaryMaths())
#     scale_tensor.inputs.operation = 'mul'
#     scale_tensor.inputs.operand_value = 1000
#     wf.connect(get_tensor, 'out_file', scale_tensor, 'in_file')
#
#     scale_tensor_eddy = scale_tensor.clone('scale_tensor_eddy')
#     wf.connect(get_tensor_eddy, 'out_file', scale_tensor_eddy, 'in_file')
#
#     # OK now that anatomical stuff (segmentation & mask)
#     # We'll need:
#     # 1. the B0 image in anat space (fslroi the 'transformed file' of voltransform
#     # 2. the aparc aseg resampled-like the B0 image (mri_convert)
#     # 3. the resample aparc_aseg binarized to be the mask image.
#
#     def binarize_aparc(aparc_aseg):
#         import nibabel as nib
#         from nipype.utils.filemanip import fname_presuffix
#         import os.path as op
#
#         img = nib.load(aparc_aseg)
#         data, aff = img.get_data(), img.affine
#         outfile = fname_presuffix(
#             aparc_aseg, suffix="bin.nii.gz",
#             newpath=op.abspath("."), use_ext=False
#         )
#         nib.Nifti1Image((data > 0).astype(float), aff).to_filename(outfile)
#         return outfile
#
#     create_mask = pe.Node(niu.Function(input_names=["aparc_aseg"],
#                                        output_names=["outfile"],
#                                        function=binarize_aparc),
#                           name="bin_aparc")
#
#     get_b0_anat = fslroi.clone('get_b0_anat')
#     wf.connect(voltransform, 'transformed_file', get_b0_anat, 'in_file')
#
#     # reslice the anat-space aparc+aseg to the DWI resolution
#     reslice_to_dwi = pe.Node(fs.MRIConvert(resample_type="nearest"),
#                              name="reslice_to_dwi")
#     wf.connect(get_b0_anat, 'roi_file', reslice_to_dwi, 'reslice_like')
#     wf.connect(inputspec, ('subjects_dir', get_aparc_aseg), reslice_to_dwi, 'in_file')
#
#     # also reslice the orig i suppose
#     reslice_orig_to_dwi = reslice_to_dwi.clone('resliceT1wToDwi')
#     wf.connect(inputspec, ('subjects_dir', get_orig), reslice_orig_to_dwi, 'in_file')
#     # reslice_orig_to_dwi.inputs.in_file = get_orig(subjects_dir, 'freesurfer')
#     reslice_orig_to_dwi.inputs.out_type = 'niigz'
#     wf.connect(get_b0_anat, 'roi_file', reslice_orig_to_dwi, 'reslice_like')
#
#     # we assume the freesurfer is the output of BIDS
#     # so the freesurfer output is in /path/to/derivatives/sub-whatever/freesurfer
#     # which means the subject_dir is /path/to/derivatives/sub-whatever
#     # reslice_to_dwi.inputs.in_file = get_aparc_aseg(subjects_dir, 'freesurfer')
#
#     # now we have a nice aparc+aseg still in anat space but resliced like the dwi file
#     # lets create a mask file from it.
#
#     wf.connect(reslice_to_dwi, 'out_file', create_mask, 'aparc_aseg')
#
#     # save all the things
#     datasink = pe.Node(nio.DataSink(), name="sinker")
#     wf.connect(inputspec, 'out_dir', datasink, 'base_directory')
#     wf.connect(inputspec, 'subject_id', datasink, 'container')
#
#     wf.connect(drop_outliers_node, "out_file", datasink, "dmriprep.dwi.@thinned")
#     wf.connect(drop_outliers_node, "out_bval", datasink, "dmriprep.dwi.@bval_thinned")
#     wf.connect(drop_outliers_node, "out_bvec", datasink, "dmriprep.dwi.@bvec_thinned")
#
#     # eddy corrected files
#     wf.connect(prep, "outputnode.out_file", datasink, "dmriprep.dwi_eddy.@corrected")
#     wf.connect(prep, "outputnode.out_bvec", datasink, "dmriprep.dwi_eddy.@rotated")
#     wf.connect(inputspec, 'bval_file', datasink, 'dmriprep.dwi_eddy.@bval')
#
#     # all the eddy stuff except the corrected files
#     wf.connect(prep, "fsl_eddy.out_movement_rms",
#                datasink, "dmriprep.qc.@eddyparamsrms")
#     wf.connect(prep, "fsl_eddy.out_outlier_report",
#                datasink, "dmriprep.qc.@eddyparamsreport")
#     wf.connect(prep, "fsl_eddy.out_restricted_movement_rms",
#                datasink, "dmriprep.qc.@eddyparamsrestrictrms")
#     wf.connect(prep, "fsl_eddy.out_shell_alignment_parameters",
#                datasink, "dmriprep.qc.@eddyparamsshellalign")
#     wf.connect(prep, "fsl_eddy.out_parameter",
#                datasink, "dmriprep.qc.@eddyparams")
#     wf.connect(prep, "fsl_eddy.out_cnr_maps",
#                datasink, "dmriprep.qc.@eddycndr")
#     wf.connect(prep, "fsl_eddy.out_residuals",
#                datasink, "dmriprep.qc.@eddyresid")
#
#     # the file that told us which volumes to drop
#     wf.connect(id_outliers_node, "outpath", datasink, "dmriprep.qc.@droppedscans")
#
#     # the tensors of the dropped volumes dwi
#     wf.connect(get_tensor, "out_file", datasink, "dmriprep.dti.@tensor")
#     wf.connect(get_tensor, "fa_file", datasink, "dmriprep.dti.@fa")
#     wf.connect(get_tensor, "md_file", datasink, "dmriprep.dti.@md")
#     wf.connect(get_tensor, "ad_file", datasink, "dmriprep.dti.@ad")
#     wf.connect(get_tensor, "rd_file", datasink, "dmriprep.dti.@rd")
#     wf.connect(get_tensor, "color_fa_file", datasink, "dmriprep.dti.@colorfa")
#     wf.connect(scale_tensor, "out_file", datasink, "dmriprep.dti.@scaled_tensor")
#
#     # the tensors of the eddied volumes dwi
#     wf.connect(get_tensor_eddy, "out_file", datasink, "dmriprep.dti_eddy.@tensor")
#     wf.connect(get_tensor_eddy, "fa_file", datasink, "dmriprep.dti_eddy.@fa")
#     wf.connect(get_tensor_eddy, "md_file", datasink, "dmriprep.dti_eddy.@md")
#     wf.connect(get_tensor_eddy, "ad_file", datasink, "dmriprep.dti_eddy.@ad")
#     wf.connect(get_tensor_eddy, "rd_file", datasink, "dmriprep.dti_eddy.@rd")
#     wf.connect(get_tensor_eddy, "color_fa_file", datasink, "dmriprep.dti_eddy.@colorfa")
#     wf.connect(scale_tensor_eddy, "out_file", datasink, "dmriprep.dti_eddy.@scaled_tensor")
#
#     # all the eddy_quad stuff
#     wf.connect(eddy_quad, 'qc_json', datasink, "dmriprep.qc.@eddyquad_json")
#     wf.connect(eddy_quad, 'qc_pdf', datasink, "dmriprep.qc.@eddyquad_pdf")
#     wf.connect(eddy_quad, 'avg_b_png', datasink, "dmriprep.qc.@eddyquad_bpng")
#     wf.connect(eddy_quad, 'avg_b0_pe_png',
#                datasink, "dmriprep.qc.@eddyquad_b0png")
#     wf.connect(eddy_quad, 'cnr_png', datasink, "dmriprep.qc.@eddyquad_cnr")
#     wf.connect(eddy_quad, 'vdm_png', datasink, "dmriprep.qc.@eddyquad_vdm")
#     wf.connect(eddy_quad, 'residuals', datasink, 'dmriprep.qc.@eddyquad_resid')
#
#     # anatomical registration stuff
#     wf.connect(bbreg, "min_cost_file", datasink, "dmriprep.reg.@mincost")
#     wf.connect(bbreg, "out_fsl_file", datasink, "dmriprep.reg.@fslfile")
#     wf.connect(bbreg, "out_reg_file", datasink, "dmriprep.reg.@reg")
#
#     # anatomical files resliced
#     wf.connect(reslice_to_dwi, 'out_file', datasink, 'dmriprep.anat.@segmentation')
#     wf.connect(create_mask, 'outfile', datasink, 'dmriprep.anat.@mask')
#     wf.connect(reslice_orig_to_dwi, 'out_file', datasink, 'dmriprep.anat.@T1w')
#
#     def report_fn(dwi_corrected_file, eddy_rms, eddy_report,
#                   color_fa_file, anat_mask_file, outlier_indices,
#                   eddy_qc_file):
#         from dmriprep.qc import create_report_json
#
#         report = create_report_json(dwi_corrected_file, eddy_rms, eddy_report,
#                                     color_fa_file, anat_mask_file, outlier_indices,
#                                     eddy_qc_file)
#         return report
#
#     report_node = pe.Node(niu.Function(
#         input_names=['dwi_corrected_file', 'eddy_rms',
#                      'eddy_report', 'color_fa_file',
#                      'anat_mask_file', 'outlier_indices', 'eddy_qc_file'],
#         output_names=['report'],
#         function=report_fn
#     ), name="reportJSON")
#
#     # for the report, lets show the eddy corrected (full volume) image
#     wf.connect(voltransform, "transformed_file", report_node, 'dwi_corrected_file')
#     wf.connect(eddy_quad, 'qc_json', report_node, 'eddy_qc_file')
#
#     # add the rms movement output from eddy
#     wf.connect(prep, "fsl_eddy.out_movement_rms", report_node, 'eddy_rms')
#     wf.connect(prep, "fsl_eddy.out_outlier_report", report_node, 'eddy_report')
#     wf.connect(id_outliers_node, 'drop_scans', report_node, 'outlier_indices')
#
#     # the mask file to check our registration, and the colorFA file go in the report
#     wf.connect(create_mask, "outfile", report_node, 'anat_mask_file')
#     wf.connect(get_tensor, "color_fa_file", report_node, 'color_fa_file')
#
#     # save that report!
#     wf.connect(report_node, 'report', datasink, 'dmriprep.report.@report')
#
#     # this part is done last, to get the filenames *just right*
#     # its super annoying.
#     def name_files_nicely(dwi_file, subject_id):
#         import os.path as op
#
#         dwi_fname = op.split(dwi_file)[1].split(".nii.gz")[0]
#         substitutions = [
#             ("vol0000_flirt_merged.nii.gz", dwi_fname + '.nii.gz'),
#             ("stats.vol0000_flirt_merged.txt", dwi_fname + ".art.json"),
#             ("motion_parameters.par", dwi_fname + ".motion.txt"),
#             ("_rotated.bvec", ".bvec"),
#             ("art.vol0000_flirt_merged_outliers.txt", dwi_fname + ".outliers.txt"),
#             ("vol0000_flirt_merged", dwi_fname),
#             ("_roi_bbreg_freesurfer", "_register"),
#             ("dwi/eddy_corrected", "dwi/%s" % dwi_fname),
#             ("dti/eddy_corrected", "dti/%s" % dwi_fname.replace("_dwi", "")),
#             ("reg/eddy_corrected", "reg/%s" % dwi_fname.replace("_dwi", "")),
#             ("aparc+aseg_outbin", dwi_fname.replace("_dwi", "_mask")),
#             ("aparc+aseg_out", dwi_fname.replace("_dwi", "_aparc+aseg")),
#             ("art.eddy_corrected_outliers", dwi_fname.replace("dwi", "outliers")),
#             ("color_fa", "colorfa"),
#             ("orig_out", dwi_fname.replace("_dwi", "_T1w")),
#             ("stats.eddy_corrected", dwi_fname.replace("dwi", "artStats")),
#             ("eddy_corrected.eddy_parameters", dwi_fname + ".eddy_parameters"),
#             ("qc/eddy_corrected", "qc/" + dwi_fname),
#             ("derivatives/dmriprep", "derivatives/{}/dmriprep".format(subject_id)),
#             ("_rotatedanat_space_thinned", ""),
#             ("_thinned", ""),
#             ("eddy_corrected", dwi_fname),
#             ("_warped", ""),
#             ("_maths", "_scaled"),
#             ("dropped_scans", dwi_fname.replace("_dwi", "_dwi_dropped_scans")),
#             ("report.json", dwi_fname.replace("_dwi", "_dwi_report.json"))
#         ]
#         return substitutions
#
#     node_name_files_nicely = pe.Node(niu.Function(input_names=['dwi_file', 'subject_id'],
#                                                   output_names=['substitutions'],
#                                                   function=name_files_nicely),
#                                      name="name_files_nicely")
#     wf.connect(inputspec, 'dwi_file', node_name_files_nicely, 'dwi_file')
#     wf.connect(inputspec, 'subject_id', node_name_files_nicely, 'subject_id')
#     wf.connect(node_name_files_nicely, 'substitutions', datasink, 'substitutions')
#
#     return wf
