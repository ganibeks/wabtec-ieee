% Development batch: retry only when the builder is edited after an error.
for attempt=1:10
 stamp=dir('build_baseline.m');
 try
  clear build_baseline validate_baseline;
  build_baseline;
  return;
 catch ME
  disp(getReport(ME,'extended','hyperlinks','off'));
  fid=fopen('development_error.txt','w'); fprintf(fid,'%s',getReport(ME,'extended','hyperlinks','off')); fclose(fid);
  changed=false;
  for wait=1:120
   pause(2); current=dir('build_baseline.m');
   if current.datenum~=stamp.datenum, changed=true; break; end
  end
  if ~changed, rethrow(ME); end
 end
end
error('Development retry limit reached');
