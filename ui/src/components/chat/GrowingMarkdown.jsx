import ReactMarkdown from 'react-markdown';

const STREAMING_MIN_HEIGHT = '4.5rem';

export default function GrowingMarkdown({ content, complete = false, className = '' }) {
  if (!content) return null;

  return (
    <div
      className={`prose prose-sm max-w-none dark:prose-invert ${className}`}
      style={{ minHeight: STREAMING_MIN_HEIGHT }}
      data-streaming-complete={complete ? 'true' : 'false'}
    >
      <ReactMarkdown>{content}</ReactMarkdown>
      {!complete && (
        <span
          className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-nn-blue align-text-bottom"
          aria-hidden="true"
        />
      )}
    </div>
  );
}
