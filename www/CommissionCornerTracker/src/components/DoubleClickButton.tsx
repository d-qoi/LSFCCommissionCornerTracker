import { createSignal, onCleanup } from 'solid-js';

interface DoubleClickButtonProps {
    onConfirm: () => void;
    initialText?: string;
    initialClass?: string;
    confirmText?: string;
    confirmClass?: string;
}

export function DoubleClickButton({
    initialText = 'Button Text',
    initialClass = 'bg-gray-200 text-black',
    confirmText = 'Click Again to Confirm',
    confirmClass = 'bg-red-600 text-white',
    onConfirm }: DoubleClickButtonProps) {

    let timeoutId: number;
    const [confirming, setConfirming] = createSignal(false);

    const handleDoubleClick = () => {
        if (confirming()) {
            onConfirm();
            setConfirming(false);
            clearTimeout(timeoutId);
        } else {
            setConfirming(true);
            timeoutId = setTimeout(() => setConfirming(false), 5000); // Optional timeout to reset the button if not clicked again
        }
    };

    onCleanup(() => clearTimeout(timeoutId));

    return (
        <button
            class={`px-4 py-2 rounded ${confirming() ? confirmClass : initialClass}`}
            onClick={handleDoubleClick}>
            {confirming() ? confirmText : initialText}
        </button>
    );
}