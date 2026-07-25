import { isImageFilePath } from './workspace-file-language';
import { normalizeEditedFilePath } from './agent-transcript-blocks';
import { normalizeGeneratedImagePath } from './thread-image-url';

/** Resolve an edit path for canvas/editor open (images keep assets/ relative form). */
export function resolveAgentEditOpenPath(
  path: string,
  projectRoot?: string | null,
): string {
  if (isImageFilePath(path)) {
    return normalizeGeneratedImagePath(path, projectRoot);
  }
  return normalizeEditedFilePath(path);
}
