import { useState, useRef, useEffect, useCallback } from 'react';
import styles from './BulletEditor.module.css';

export interface BulletPoint {
  id: string;
  section: string;
  text: string;
  order: number;
  edited: boolean;
}

export interface BulletEditorProps {
  bullet: BulletPoint;
  onUpdate: (id: string, text: string) => void;
  onDelete: (id: string) => void;
  onMoveUp: (id: string) => void;
  onMoveDown: (id: string) => void;
  isFirst: boolean;
  isLast: boolean;
}

function BulletEditor({
  bullet,
  onUpdate,
  onDelete,
  onMoveUp,
  onMoveDown,
  isFirst,
  isLast,
}: BulletEditorProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(bullet.text);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const cancelRef = useRef(false);

  /* Sync draft when bullet text changes externally */
  useEffect(() => {
    if (!editing) {
      setDraft(bullet.text);
    }
  }, [bullet.text, editing]);

  /* Focus and select textarea on entering edit mode */
  useEffect(() => {
    if (editing && textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.select();
    }
  }, [editing]);

  const save = useCallback(() => {
    const trimmed = draft.trim();
    if (trimmed && trimmed !== bullet.text) {
      onUpdate(bullet.id, trimmed);
    }
  }, [draft, bullet.id, bullet.text, onUpdate]);

  const handleStartEdit = useCallback(() => {
    setDraft(bullet.text);
    setEditing(true);
  }, [bullet.text]);

  const handleBlur = useCallback(() => {
    /* Skip save if we just handled Enter/Escape (prevents double-save) */
    if (cancelRef.current) {
      cancelRef.current = false;
      return;
    }
    save();
    setEditing(false);
  }, [save]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        cancelRef.current = true;
        setDraft(bullet.text);
        setEditing(false);
      } else if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        cancelRef.current = true;
        save();
        setEditing(false);
      }
    },
    [bullet.text, save],
  );

  return (
    <div className={`${styles.container} ${editing ? styles.editing : ''}`}>
      {editing ? (
        /* ── Edit mode ── */
        <div className={styles.editArea}>
          <textarea
            ref={textareaRef}
            className={styles.textarea}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={handleBlur}
            aria-label="Edit bullet text"
          />
          <div className={styles.editHint}>
            <span>↵ Enter to save</span>
            <span>·</span>
            <span>Esc to cancel</span>
          </div>
        </div>
      ) : (
        /* ── Display mode ── */
        <div
          className={styles.display}
          onClick={handleStartEdit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleStartEdit();
          }}
          role="button"
          tabIndex={0}
          aria-label="Click to edit bullet"
        >
          <div className={styles.textContent}>
            {bullet.text}
            {bullet.edited && (
              <span className={styles.editedBadge}>
                <span className={styles.editedDot} />
                edited
              </span>
            )}
          </div>

          <div
            className={styles.actions}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className={styles.actionBtn}
              disabled={isFirst}
              onClick={() => onMoveUp(bullet.id)}
              title="Move up"
              aria-label="Move bullet up"
            >
              ↑
            </button>
            <button
              className={styles.actionBtn}
              disabled={isLast}
              onClick={() => onMoveDown(bullet.id)}
              title="Move down"
              aria-label="Move bullet down"
            >
              ↓
            </button>
            <button
              className={`${styles.actionBtn} ${styles.deleteBtn}`}
              onClick={() => onDelete(bullet.id)}
              title="Delete"
              aria-label="Delete bullet"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default BulletEditor;
