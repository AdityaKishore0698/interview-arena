with open("frontend/src/components/interview/InterviewWorkspace.tsx", "r") as f:
    content = f.read()

replacement = """
        ) : (
            <div className="h-full flex flex-col mx-auto space-y-6 max-w-[1200px] w-full">
              <div className="space-y-2">
                <h3 className="text-2xl font-medium tracking-tight text-foreground flex items-center justify-between">
                  <span>{role === 'INTERVIEWER' ? 'You are the Interviewer' : 'You are the Interviewee'}</span>
                  <span className="text-sm px-3 py-1 bg-primary/10 text-primary rounded-full uppercase tracking-widest">{roomName}</span>
                </h3>
              </div>
              
              <div className="flex-1 flex flex-col md:flex-row gap-6 relative">
                 {/* Problem Prompt / Context Panel */}
                 <div className="flex-[4] flex flex-col rounded-xl border border-border/40 bg-background/50 overflow-hidden">
                    <div className="px-4 py-3 border-b border-border/40 bg-surface/50 text-xs font-semibold tracking-widest uppercase text-muted-foreground flex justify-between">
                      <span>{roomName.includes('System Design') ? 'Architecture Requirements' : 'Problem Description'}</span>
                    </div>
                    <div className="p-6 text-sm text-foreground/90 leading-relaxed overflow-y-auto">
                      {role === 'INTERVIEWER' ? (
                        <div className="space-y-4">
                           <p className="font-medium text-primary">Interviewer Instructions:</p>
                           <p>Provide the candidate with a question relevant to {roomName}. You may paste the question details below or communicate them verbally.</p>
                           <textarea 
                             className="w-full h-48 bg-surface border border-border/50 rounded-lg p-4 resize-none outline-none font-mono text-sm mt-4 focus:border-primary/50"
                             placeholder="Paste question description here..."
                             spellCheck={false}
                           />
                        </div>
                      ) : (
                        <div className="space-y-4">
                           <p className="font-medium">Waiting for Interviewer...</p>
                           <p className="text-muted-foreground">The interviewer will provide the question verbally or paste it here. Use the scratchpad to take notes.</p>
                        </div>
                      )}
                    </div>
                 </div>

                 {/* Scratchpad Panel */}
                 <div className="flex-[6] flex flex-col rounded-xl border border-border/40 bg-background/50 overflow-hidden shadow-lg">
                    <div className="px-4 py-3 border-b border-border/40 bg-surface/50 text-xs font-semibold tracking-widest uppercase text-muted-foreground flex justify-between">
                      <span>{roomName.includes('System Design') ? 'Design Notes / Components' : 'Code / Scratchpad'} (Local)</span>
                    </div>
                    <textarea 
                      className="flex-1 w-full bg-transparent p-6 resize-none outline-none font-mono text-sm leading-relaxed focus:ring-1 focus:ring-inset focus:ring-primary/20"
                      placeholder={roomName.includes('System Design') ? "Type your design components, API contracts, or reasoning here..." : "Type your code or logic here..."}
                      spellCheck={false}
                    />
                 </div>
              </div>
            </div>
        )}
"""
import re
content = re.sub(r"\)\s*:\s*\(\s*<div className=\"h-full flex flex-col max-w-4xl mx-auto space-y-6\">.*?\)\}", replacement + "\n      </div>\n    </div>\n  );\n}", content, flags=re.DOTALL)

with open("frontend/src/components/interview/InterviewWorkspace.tsx", "w") as f:
    f.write(content)
