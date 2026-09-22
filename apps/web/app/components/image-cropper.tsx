'use client';

import { useEffect, useRef, useState } from 'react';

type Props = {
  file: File;
  aspect: number;
  title: string;
  onCancel: () => void;
  onConfirm: (dataUrl: string) => void;
};

export function ImageCropper({ file, aspect, title, onCancel, onConfirm }: Props) {
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  const [zoom, setZoom] = useState(1);
  const [x, setX] = useState(0);
  const [y, setY] = useState(0);
  const [preview, setPreview] = useState('');
  const cancelButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = originalOverflow;
    };
  }, []);
  useEffect(() => {
    cancelButton.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onCancel();
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [onCancel]);
  useEffect(() => {
    const url = URL.createObjectURL(file);
    const source = new Image();
    source.onload = () => setImage(source);
    source.src = url;
    return () => URL.revokeObjectURL(url);
  }, [file]);
  useEffect(() => {
    if (!image) return;
    const baseWidth = image.width / image.height > aspect ? image.height * aspect : image.width;
    const baseHeight = baseWidth / aspect;
    const cropWidth = baseWidth / zoom;
    const cropHeight = baseHeight / zoom;
    const sourceX = ((image.width - cropWidth) * (x + 1)) / 2;
    const sourceY = ((image.height - cropHeight) * (y + 1)) / 2;
    const canvas = document.createElement('canvas');
    canvas.width = 1200;
    canvas.height = Math.round(1200 / aspect);
    canvas
      .getContext('2d')
      ?.drawImage(
        image,
        sourceX,
        sourceY,
        cropWidth,
        cropHeight,
        0,
        0,
        canvas.width,
        canvas.height,
      );
    setPreview(canvas.toDataURL('image/png'));
  }, [image, zoom, x, y, aspect]);
  return (
    <div className="crop-backdrop" role="dialog" aria-modal="true" aria-labelledby="crop-title">
      <section className="crop-dialog">
        <div>
          <p className="eyebrow">IMAGE EDITOR</p>
          <h2 id="crop-title">{title}</h2>
          <p>Zoom and position your image, then save the crop.</p>
        </div>
        <div
          className={`crop-preview ${aspect === 1 ? 'square' : 'wide'}`}
          style={{ aspectRatio: String(aspect) }}
        >
          {preview && <img src={preview} alt="Crop preview" />}
        </div>
        <div className="crop-controls">
          <label>
            Zoom
            <input
              type="range"
              min="1"
              max="3"
              step="0.05"
              value={zoom}
              onChange={(event) => setZoom(Number(event.target.value))}
            />
          </label>
          <label>
            Horizontal
            <input
              type="range"
              min="-1"
              max="1"
              step="0.02"
              value={x}
              onChange={(event) => setX(Number(event.target.value))}
            />
          </label>
          <label>
            Vertical
            <input
              type="range"
              min="-1"
              max="1"
              step="0.02"
              value={y}
              onChange={(event) => setY(Number(event.target.value))}
            />
          </label>
        </div>
        <div className="crop-actions">
          <button ref={cancelButton} onClick={onCancel}>
            Cancel
          </button>
          <button className="button" disabled={!preview} onClick={() => onConfirm(preview)}>
            Use cropped image
          </button>
        </div>
      </section>
    </div>
  );
}
