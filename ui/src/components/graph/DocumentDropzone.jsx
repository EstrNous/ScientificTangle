import { useDropzone } from 'react-dropzone';

export default function DocumentDropzone({ onUpload }) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (files) => onUpload?.(files),
  });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded p-6 text-center text-sm cursor-pointer ${
        isDragActive ? 'border-indigo-500 bg-slate-900' : 'border-slate-700'
      }`}
    >
      <input {...getInputProps()} />
      Перетащите PDF/DOCX или нажмите для выбора
    </div>
  );
}
