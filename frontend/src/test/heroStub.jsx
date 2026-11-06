import React from 'react';
// Jest 27 can't read the package `exports` HeroUI's dependencies use, so unit tests swap in these thin stand-ins. The real components are checked in the browser.
const noRac = ({ onPress, isDisabled, isIconOnly, fullWidth, variant, size, ...p }) => ({ ...p, ...(onPress ? { onClick: onPress } : {}), ...(isDisabled ? { disabled: true } : {}) });
export const Button = React.forwardRef((p, ref) => <button type="button" ref={ref} {...noRac(p)} />);
export const TextArea = React.forwardRef((p, ref) => <textarea ref={ref} {...noRac(p)} />);
export const Surface = ({ variant, ...p }) => <div {...p} />;
const Ctx = React.createContext(false);
export const Popover = ({ isOpen, onOpenChange, children }) => {
  const [trigger, ...rest] = React.Children.toArray(children);
  return <Ctx.Provider value={isOpen}>{React.cloneElement(trigger, { onClick: () => onOpenChange?.(!isOpen) })}{rest}</Ctx.Provider>;
};
Popover.Content = function Content({ children, placement, offset, ...p }) { return React.useContext(Ctx) ? <div {...p}>{children}</div> : null; };
Popover.Dialog = function Dialog(p) { return <div role="dialog" {...p} />; };
export const ProgressCircle = ({ children, value, ...p }) => <div role="progressbar" aria-valuenow={value} {...p}>{children}</div>;
ProgressCircle.Track = ({ children }) => <svg>{children}</svg>; ProgressCircle.TrackCircle = () => <circle />; ProgressCircle.FillCircle = () => <circle />;
