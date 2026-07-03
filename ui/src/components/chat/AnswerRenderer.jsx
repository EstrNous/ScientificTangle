import ReactMarkdown from 'react-markdown';
import EvidenceTable from './EvidenceTable.jsx';
import SynonymTransparency from './SynonymTransparency.jsx';
import SourceCitation from './SourceCitation.jsx';
import WarningsPanel from './WarningsPanel.jsx';

export default function AnswerRenderer({ message }) {
  return (
    <div className="space-y-3 text-sm">
      <ReactMarkdown>{message.content}</ReactMarkdown>
      {message.evidence_table && <EvidenceTable table={message.evidence_table} />}
      {message.sources?.length > 0 && (
        <div className="space-y-2">
          {message.sources.map((s, i) => (
            <SourceCitation key={i} source={s} />
          ))}
        </div>
      )}
      {message.expanded_synonyms && (
        <SynonymTransparency synonyms={message.expanded_synonyms} />
      )}
      {message.confidence != null && (
        <WarningsPanel confidence={message.confidence} />
      )}
    </div>
  );
}
