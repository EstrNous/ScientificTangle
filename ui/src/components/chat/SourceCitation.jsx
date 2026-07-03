import SourceLink from '../shared/SourceLink.jsx';

export default function SourceCitation({ source }) {
  return (
    <div className="rounded-lg border border-nn-border bg-nn-gray-light p-2 text-xs dark:border-slate-600 dark:bg-slate-800">
      <p className="font-medium text-gray-900 dark:text-slate-100">
        <SourceLink source={source}>{source.title}</SourceLink>
      </p>
      <p className="text-nn-gray dark:text-slate-400">
        <SourceLink source={source} className="text-nn-gray dark:text-slate-400 hover:text-nn-blue dark:hover:text-sky-400">
          {source.author}
        </SourceLink>
        {' · '}
        {source.date}
        {' · '}
        {source.confidence_level}
      </p>
    </div>
  );
}
