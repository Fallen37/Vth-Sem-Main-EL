import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

export interface ExplanationCard {
  id: string;
  topic: string;
  explanation: string;
  metaText?: string;
  liked?: boolean;
  iterationLevel: number;
  createdAt: string;
}

export interface LearningContextType {
  currentCard: ExplanationCard | null;
  setCurrentCard: (card: ExplanationCard) => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  showMetaText: boolean;
  setShowMetaText: (show: boolean) => void;
  notebookEntries: ExplanationCard[];
  setNotebookEntries: (entries: ExplanationCard[]) => void;
  updateCardFeedback: (cardId: string, liked: boolean) => void;
  replaceCardExplanation: (cardId: string, newExplanation: string, iterationLevel: number) => void;
}

const LearningContext = createContext<LearningContextType | undefined>(undefined);

export const LearningProvider = ({ children }: { children: ReactNode }) => {
  const [currentCard, setCurrentCard] = useState<ExplanationCard | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showMetaText, setShowMetaText] = useState(false);
  const [notebookEntries, setNotebookEntries] = useState<ExplanationCard[]>([]);

  const updateCardFeedback = useCallback((cardId: string, liked: boolean) => {
    if (currentCard && currentCard.id === cardId) {
      setCurrentCard({
        ...currentCard,
        liked,
      });
    }
  }, [currentCard]);

  const replaceCardExplanation = useCallback((cardId: string, newExplanation: string, iterationLevel: number) => {
    if (currentCard && currentCard.id === cardId) {
      setCurrentCard({
        ...currentCard,
        explanation: newExplanation,
        iterationLevel,
        liked: undefined,
      });
    }
  }, [currentCard]);

  return (
    <LearningContext.Provider
      value={{
        currentCard,
        setCurrentCard,
        isLoading,
        setIsLoading,
        showMetaText,
        setShowMetaText,
        notebookEntries,
        setNotebookEntries,
        updateCardFeedback,
        replaceCardExplanation,
      }}
    >
      {children}
    </LearningContext.Provider>
  );
};

export const useLearning = () => {
  const context = useContext(LearningContext);
  if (context === undefined) {
    throw new Error('useLearning must be used within a LearningProvider');
  }
  return context;
};
