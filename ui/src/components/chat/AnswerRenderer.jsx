import ReactMarkdown from 'react-markdown';
import { extractScientificAnswer, normalizeWarnings } from '../../utils/answerPayload.js';
import EvidenceTable from './EvidenceTable.jsx';
import ScientificAnswerView from './ScientificAnswerView.jsx';
import SynonymTransparency from './SynonymTransparency.jsx';
import SourceCitation from './SourceCitation.jsx';
import WarningsPanel from './WarningsPanel.jsx';

function LegacyAnswerView({ message }) {
  return (
    <>
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
    </>
  );
}

export default function AnswerRenderer({ message }) {
  const scientificAnswer = extractScientificAnswer(message);
  const warnings = normalizeWarnings(message.warnings);

  return (
    <div className="min-w-0 space-y-3 text-sm break-words">
      {scientificAnswer ? (
        <ScientificAnswerView answer={scientificAnswer} message={message} />
      ) : (
        <LegacyAnswerView message={message} />
      )}
      {scientificAnswer && message.evidence_table && (
        <EvidenceTable table={message.evidence_table} />
      )}
      {scientificAnswer && message.sources?.length > 0 && (
        <div className="space-y-2">
          {message.sources.map((s, i) => (
            <SourceCitation key={i} source={s} />
          ))}
        </div>
      )}
      {scientificAnswer && message.expanded_synonyms && (
        <SynonymTransparency synonyms={message.expanded_synonyms} />
      )}
      <WarningsPanel confidence={message.confidence} warnings={warnings} />
    </div>
  );
}
