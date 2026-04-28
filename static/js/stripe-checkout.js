document.addEventListener('DOMContentLoaded', function() {
    const buyButton = document.getElementById('buy-button');

    if (!buyButton) {
        console.error('Buy button not found');
        return;
    }

    buyButton.addEventListener('click', function() {
        const itemId = buyButton.getAttribute('data-item-id');
        const stripePublicKey = buyButton.getAttribute('data-stripe-key');

        if (!itemId || !stripePublicKey) {
            console.error('Missing data-item-id or data-stripe-key on button');
            return;
        }

        const stripe = Stripe(stripePublicKey);

        fetch('/buy/' + itemId + '/')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Server returned ' + response.status);
                }
                return response.json();
            })
            .then(data => {
                if (data.session_id) {
                    return stripe.redirectToCheckout({ sessionId: data.session_id });
                } else {
                    console.error('No session_id in response:', data);
                    alert('Error: no session_id');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Something went wrong: ' + error.message);
            });
    });
});
