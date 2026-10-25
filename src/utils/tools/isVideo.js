export default function isVideo(filename) {
    const index = filename.lastIndexOf('.');
    if (index < 0) return false;
    const ext = filename.slice(index + 1).toUpperCase();
    return ext === 'MP4';
}
