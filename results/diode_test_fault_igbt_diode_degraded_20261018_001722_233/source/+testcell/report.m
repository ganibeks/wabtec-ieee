function reportFile = report(folder)
% Portable HTML summary of an executed experiment; adjacent CSV/MAT are evidence.
file=fullfile(folder,'validation.json'); assert(isfile(file),'No completed validation record.');
record=jsondecode(fileread(file));
reportFile=fullfile(folder,'report.html'); assert(~isfile(reportFile),'Report already exists; preserve it.');
f=fopen(reportFile,'w'); cleanup=onCleanup(@()fclose(f)); %#ok<NASGU>
fprintf(f,'<!doctype html><html lang="en"><meta charset="utf-8"><title>IGBT electrical laboratory report</title>');
fprintf(f,'<style>body{font:16px Arial;max-width:1100px;margin:32px auto;color:#172333}img{width:100%%}pre{white-space:pre-wrap;background:#f2f4f6;padding:16px}li{margin:8px}</style>');
fprintf(f,'<h1>IGBT electrical laboratory: assumed-device experiment</h1>');
fprintf(f,'<p><b>Hardware health decision: INCONCLUSIVE.</b> No module identity, measured calibration data, safe operating area or approved acceptance limits supplied.</p>');
fprintf(f,'<p>Numerical validation checks circuit equations, parameter recovery and/or step convergence. It does not certify a physical module. Models use explicit illustrative device and fixture parameters.</p>');
fprintf(f,'<h2>Executed validation record</h2><pre>%s</pre>',escape(jsonencode(record,PrettyPrint=true)));
fprintf(f,'<h2>Parameters and provenance</h2><pre>%s</pre>',escape(fileread(fullfile(folder,'parameters.json'))));
fprintf(f,'<h2>Results</h2>');
plots=dir(fullfile(folder,'*.png'));
for k=1:numel(plots), fprintf(f,'<p>%s</p><img src="%s" alt="%s">',escape(plots(k).name),plots(k).name,escape(plots(k).name)); end
fprintf(f,'<h2>Numerical evidence</h2><ul>');
for pattern={'*.csv','*.json','*.slx','*_raw.mat'}
 files=dir(fullfile(folder,pattern{1}));
 for k=1:numel(files), fprintf(f,'<li><a href="%s">%s</a></li>',files(k).name,escape(files(k).name)); end
end
fprintf(f,'</ul><h2>Interpretation limits</h2><p>Static temperature is imposed, not self-heating. The current diode has conduction and junction capacitance but no reverse-recovery charge. Event collector-terminal energy includes conduction and reactive transfer; it is not calibrated switching dissipation. No thermal coupling, fault detection or protection timing is implied by these electrical results.</p></html>');
end
function x=escape(x)
x=strrep(x,'&','&amp;'); x=strrep(x,'<','&lt;'); x=strrep(x,'>','&gt;');
end
