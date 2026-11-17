#nullable enable
using System;
using Rhino;
using Rhino.Commands;

namespace AlmondEngine
{
    /// <summary>One modeless Undo owner. Empty records and another owner's history are never undone.</summary>
    public static class NativeUndoRecord
    {
        public static bool Owns(RhinoDoc doc, uint undoSn)
        {
            return undoSn != 0 && doc.UndoRecordingIsActive &&
                doc.CurrentUndoRecordSerialNumber == undoSn;
        }

        public static void Finish(RhinoDoc doc, uint undoSn, bool rollback)
        {
            if (!Owns(doc, undoSn))
                throw new InvalidOperationException("The operation changed its Undo record. Automatic rollback was skipped to protect other work.");

            bool purged = false;
            int ownerThreadId = System.Environment.CurrentManagedThreadId;
            uint nextUndoSn = doc.NextUndoRecordSerialNumber;
            EventHandler<UndoRedoEventArgs> onUndoRedo = (sender, e) =>
            {
                if (System.Environment.CurrentManagedThreadId == ownerThreadId &&
                    e.UndoSerialNumber == undoSn && e.IsPurgeRecord)
                    purged = true;
            };

            // Rhino discards empty records during EndUndoRecord and reports their
            // serial via IsPurgeRecord. Undoing after that would undo earlier work.
            // Observe only this synchronous close; no custom marker is needed,
            // so an empty failure also preserves an existing Redo history.
            Command.UndoRedo += onUndoRedo;
            try
            {
                if (!doc.EndUndoRecord(undoSn))
                    throw new InvalidOperationException("Could not close the operation's Undo record.");
            }
            finally
            {
                Command.UndoRedo -= onUndoRedo;
            }

            if (!rollback || purged)
                return;

            if (doc.UndoRecordingIsActive || doc.UndoActive || doc.RedoActive ||
                doc.NextUndoRecordSerialNumber != nextUndoSn)
                throw new InvalidOperationException("Undo state changed while closing the operation's record. Automatic rollback was skipped to protect other work.");

            try
            {
                if (!doc.Undo())
                    throw new InvalidOperationException("Rhino could not undo the failed operation's record.");
            }
            finally
            {
                // Modeless Undo starts its own record. No Rhino command will end
                // it for us; leaving it open keeps UndoActive true indefinitely.
                if (doc.UndoRecordingIsActive)
                {
                    if (!Owns(doc, nextUndoSn))
                        throw new InvalidOperationException("Undo recovery encountered another active record and left it under its owner's control.");
                    if (!doc.EndUndoRecord(nextUndoSn))
                        throw new InvalidOperationException("Could not close the rollback Undo record.");
                }

                if (doc.UndoRecordingIsActive || doc.UndoActive || doc.RedoActive)
                    throw new InvalidOperationException("Rhino still reports an active Undo/Redo operation after recovery.");
            }

            // Undo puts the failed nonempty script on Redo. Once recovery has
            // completed, discard that history so Redo cannot replay partial edits.
            // Keep this outside finally: failed recovery must retain its history.
            doc.ClearRedoRecords();
        }
        public static MutationOutcome Run(RhinoDoc doc, string name, Action action)
        {
            uint serial = doc.BeginUndoRecord(name);
            if (serial == 0) return new MutationOutcome(false, "none", "Cannot acquire an Undo record. Finish the current command before retrying.");
            Exception? failure = null;
            try { action(); }
            catch (Exception ex) { failure = ex; }
            try
            {
                Finish(doc, serial, failure != null);
                return failure == null ? new MutationOutcome(true, "completed", null)
                    : new MutationOutcome(false, "rolled_back", failure.Message + " The operation's changes were rolled back.");
            }
            catch (Exception ex)
            {
                return new MutationOutcome(false, "unknown", (failure?.Message + " " + ex.Message).Trim() +
                    " Completion is uncertain; inspect the document before retrying.");
            }
            finally
            {
                // Never close a record belonging to a reentrant command or script.
                try { if (Owns(doc, serial)) doc.EndUndoRecord(serial); }
                catch { /* Finish already reported uncertain ownership; do not mask its evidence. */ }
            }
        }
    }
    public sealed record MutationOutcome(bool Success, string State, string? Error);
}
