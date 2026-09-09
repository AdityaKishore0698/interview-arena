import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { api } from '@/lib/api';
import { Loader2, CheckCircle2 } from 'lucide-react';

type Scores = {
  communication: number;
  technicalKnowledge: number;
  problemSolving: number;
};

// Hoisted outside component — prevents re-creation during render
function RatingRow({
  label,
  field,
  scores,
  onSelect,
}: {
  label: string;
  field: keyof Scores;
  scores: Scores;
  onSelect: (field: keyof Scores, val: number) => void;
}) {
  return (
    <div className="flex items-center justify-between p-4 bg-surface hover:bg-surface/80 transition-colors rounded-2xl">
      <span className="text-base font-medium tracking-tight text-foreground">{label}</span>
      <div className="flex space-x-2" role="radiogroup" aria-label={label}>
        {[1, 2, 3, 4, 5].map((val) => (
          <button
            key={val}
            type="button"
            role="radio"
            aria-checked={scores[field] === val}
            onClick={() => onSelect(field, val)}
            className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
              scores[field] === val 
                ? 'bg-primary text-primary-foreground shadow-md scale-110' 
                : 'bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground'
            }`}
          >
            {val}
          </button>
        ))}
      </div>
    </div>
  );
}

export function FeedbackForm({ sessionId, roundId, evaluatedRole, roundLabel }: { sessionId: string; roundId: string, evaluatedRole: string, roundLabel: string }) {
  const [scores, setScores] = useState<Scores>({
    communication: 0,
    technicalKnowledge: 0,
    problemSolving: 0
  });
  const [comments, setComments] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const isValid = scores.communication > 0 && scores.technicalKnowledge > 0 && scores.problemSolving > 0;

  const handleSelect = (field: keyof Scores, val: number) => {
    setScores(s => ({ ...s, [field]: val }));
  };

  const handleSubmit = async () => {
    if (!isValid) return;
    setIsSubmitting(true);
    setError("");
    try {
      await api.post(`/api/v1/sessions/${sessionId}/rounds/${roundId}/feedback`, {
        scores,
        comments
      });
      setSubmitted(true);
    } catch (err: unknown) {
      const e = err as { response?: { status?: number, data?: { detail?: string } } };
      if (e.response?.status === 409) {
        setSubmitted(true); // Already submitted — idempotent
      } else {
        setError(e.response?.data?.detail || "Failed to submit feedback");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="w-full flex-1 flex flex-col items-center justify-center p-12 space-y-4 animate-in fade-in duration-700">
        <div className="bg-success/10 p-4 rounded-full">
          <CheckCircle2 className="w-10 h-10 text-success" />
        </div>
        <h3 className="text-2xl font-semibold tracking-tight text-foreground">Feedback Submitted</h3>
        <p className="text-muted-foreground text-center max-w-sm">
          Waiting for the server to transition the session state...
        </p>
      </div>
    );
  }

  return (
    <div className="w-full flex-1 flex flex-col max-w-3xl mx-auto px-4 md:px-8 py-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      <header className="mb-10 text-center space-y-2">
        <h2 className="text-3xl font-semibold tracking-tight text-foreground">Evaluating {evaluatedRole}</h2>
        <p className="text-muted-foreground">
          {roundLabel} • Provide constructive feedback on their performance
        </p>
      </header>

      <div className="space-y-4 mb-10">
        <RatingRow label="Communication" field="communication" scores={scores} onSelect={handleSelect} />
        <RatingRow label="Technical Knowledge" field="technicalKnowledge" scores={scores} onSelect={handleSelect} />
        <RatingRow label="Problem Solving" field="problemSolving" scores={scores} onSelect={handleSelect} />
      </div>
      
      <div className="space-y-3 mb-10">
        <label className="text-sm font-semibold tracking-widest uppercase text-muted-foreground ml-2">Comments (Optional)</label>
        <Textarea 
          placeholder="Constructive feedback, specific observations..." 
          value={comments}
          onChange={(e) => setComments(e.target.value)}
          className="min-h-[160px] resize-none bg-surface/50 border-border/40 focus-visible:ring-primary/30 rounded-2xl p-5 text-base"
          disabled={isSubmitting}
        />
      </div>
      
      {error && <p className="text-destructive text-sm font-medium mb-6 text-center" aria-live="polite">{error}</p>}
      
      <div className="flex justify-center">
        <Button 
          onClick={handleSubmit} 
          disabled={isSubmitting || !isValid}
          size="lg"
          className="h-14 rounded-full border-0 bg-primary-gradient px-12 font-semibold text-white shadow-glow transition-all duration-300 hover:scale-[1.02] hover:shadow-glow-strong active:scale-[0.98]"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin mr-3 opacity-70" />
              Submitting...
            </>
          ) : (
            'Submit Feedback'
          )}
        </Button>
      </div>
    </div>
  );
}
