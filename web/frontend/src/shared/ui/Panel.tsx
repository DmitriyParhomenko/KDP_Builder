import type { PropsWithChildren } from 'react';

type PanelProps = PropsWithChildren<{
  title?: string;
  className?: string;
}>;

const Panel = ({ title, className = '', children }: PanelProps) => (
  <div className={`p-4 ${className}`}>
    {title ? (
      <h3 className="text-sm font-semibold text-gray-400 mb-4">{title}</h3>
    ) : null}
    {children}
  </div>
);

export default Panel;

