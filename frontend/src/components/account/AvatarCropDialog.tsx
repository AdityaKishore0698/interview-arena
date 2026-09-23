'use client';

import { useState } from 'react';
import Cropper, { type Area } from 'react-easy-crop';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { ZoomIn } from 'lucide-react';

const OUTPUT_DIMENSION = 256; // px, square

/** Draws the region the user selected (in the original image's own pixel
 * coordinates, as react-easy-crop reports it) onto a fixed-size canvas, so
 * the stored avatar is always a small square regardless of the source
 * photo's size or aspect ratio. */
function cropToDataUri(imageSrc: string, area: Area): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onerror = () => reject(new Error('Could not load the image.'));
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = OUTPUT_DIMENSION;
      canvas.height = OUTPUT_DIMENSION;
      const ctx = canvas.getContext('2d');
      if (!ctx) { reject(new Error('Could not process the image.')); return; }
      ctx.drawImage(
        img,
        area.x, area.y, area.width, area.height,
        0, 0, OUTPUT_DIMENSION, OUTPUT_DIMENSION
      );
      resolve(canvas.toDataURL('image/jpeg', 0.85));
    };
    img.src = imageSrc;
  });
}

interface AvatarCropDialogProps {
  imageSrc: string | null;
  onCancel: () => void;
  onConfirm: (dataUri: string) => void;
}

export function AvatarCropDialog({ imageSrc, onCancel, onConfirm }: AvatarCropDialogProps) {
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState<Area | null>(null);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleOpenChange = (open: boolean) => {
    if (!open) onCancel();
  };

  const handleConfirm = async () => {
    if (!imageSrc || !croppedAreaPixels) return;
    setProcessing(true);
    setError(null);
    try {
      const dataUri = await cropToDataUri(imageSrc, croppedAreaPixels);
      onConfirm(dataUri);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not crop that image.');
    } finally {
      setProcessing(false);
    }
  };

  return (
    <Dialog open={!!imageSrc} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Position your photo</DialogTitle>
          <DialogDescription>
            Drag to reposition, and use the slider to zoom. The circle shows what will be used.
          </DialogDescription>
        </DialogHeader>

        {imageSrc && (
          <div className="relative h-72 w-full overflow-hidden rounded-xl bg-black/40">
            <Cropper
              image={imageSrc}
              crop={crop}
              zoom={zoom}
              aspect={1}
              cropShape="round"
              showGrid={false}
              objectFit="cover"
              minZoom={1}
              maxZoom={4}
              onCropChange={setCrop}
              onZoomChange={setZoom}
              onCropComplete={(_area, areaPixels) => setCroppedAreaPixels(areaPixels)}
            />
          </div>
        )}

        <div className="flex items-center gap-3 px-1">
          <ZoomIn className="h-4 w-4 shrink-0 text-muted-foreground" />
          <input
            type="range"
            min={1}
            max={4}
            step={0.01}
            value={zoom}
            onChange={(e) => setZoom(Number(e.target.value))}
            className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-border accent-primary"
            aria-label="Zoom"
          />
        </div>

        {error && <p className="text-sm text-destructive" aria-live="polite">{error}</p>}

        <DialogFooter className="mt-2 flex justify-end space-x-2">
          <Button type="button" variant="outline" onClick={onCancel} disabled={processing}>
            Cancel
          </Button>
          <Button type="button" onClick={handleConfirm} disabled={processing || !croppedAreaPixels}>
            Use this photo
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
