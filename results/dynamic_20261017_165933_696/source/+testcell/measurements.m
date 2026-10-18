function x = measurements(out,names)
% Use solver timestamps, without reducing the switching transient to a coarse grid.
[t,ix]=unique(out.Ic.Time,'last'); x.t=t;
for k=1:numel(names)
 s=out.(names{k}); [ts,j]=unique(s.Time,'last');
 if isequal(ts,t), value=s.Data(j); else, value=interp1(ts,s.Data(j),t,'linear'); end
 assert(all(isfinite(value)),'Nonfinite measurement %s',names{k});
 x.(names{k})=value(:);
end
assert(all(diff(t)>0),'Non-increasing solver times');
end
