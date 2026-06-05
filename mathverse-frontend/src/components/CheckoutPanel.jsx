import React, { useState } from 'react';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const requestTimeoutMs = 15000;

export default function CheckoutPanel({ userId, grade, onSubscriptionUnlocked }) {
  const [promoCode, setPromoCode] = useState('');
  const [billingMessage, setBillingMessage] = useState('Standard Grade Subscription: ₹500/month');
  const [isLoading, setIsLoading] = useState(false);

  const loadRazorpayScript = () => {
    return new Promise((resolve) => {
      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.onload = () => resolve(true);
      script.onerror = () => resolve(false);
      document.body.appendChild(script);
    });
  };

  const handleCheckout = async () => {
    setIsLoading(true);
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), requestTimeoutMs);
    try {
      const response = await fetch(`${apiBaseUrl}/api/payments/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          user_id: userId,
          grade: String(grade),
          promo_code: promoCode ? promoCode : null
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Checkout submission initialization failed.");
      }

      // PATH A: Free Trial/BETA100 Promo Code Activated (Bypasses Gateways)
      if (data.payment_required === false) {
        alert(data.message);
        onSubscriptionUnlocked();
        return;
      }

      // PATH B: Paid Gateway Execution via Razorpay Checkout Overlay
      const scriptLoaded = await loadRazorpayScript();
      if (!scriptLoaded) {
        alert("Razorpay payment gateway failed to fetch. Check network connection.");
        return;
      }

      const options = {
        key: "YOUR_RAZORPAY_KEY_ID", // Input standard test credential from your account dashboard
        amount: data.final_amount_charged * 100, // Converts rupees value directly to paisa unit
        currency: "INR",
        name: "MathVerse Platform",
        description: `Grade ${grade} Monthly Subscription Access`,
        order_id: data.razorpay_order_id,
        handler: async function (paymentResponse) {
          // Razorpay success callback interceptor
          alert("Payment Received! Transaction Reference ID: " + paymentResponse.razorpay_payment_id);
          // Trigger data reload step on frontend
          onSubscriptionUnlocked();
        },
        prefill: { name: "Student User" },
        theme: { color: "#4F46E5" }
      };

      const paymentWindow = new window.Razorpay(options);
      paymentWindow.open();

    } catch (error) {
      const message = error?.name === "AbortError" ? "Checkout timed out. Check that the backend is ready and Firestore credentials are configured." : error.message;
      alert("Checkout error: " + message);
    } finally {
      window.clearTimeout(timeoutId);
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-md mt-10 border border-indigo-100">
      <h3 className="text-xl font-bold mb-4 text-gray-800">Unlock Grade {grade} Class Access</h3>
      <p className="text-sm text-gray-600 mb-6">{billingMessage}</p>

      <div className="mb-4">
        <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Have a Promo Code?</label>
        <div className="flex gap-2">
          <input type="text" placeholder="e.g. BETA100 or MATH20" value={promoCode} onChange={(e) => setPromoCode(e.target.value.toUpperCase())} className="flex-1 p-2 border rounded uppercase tracking-wider font-mono" />
        </div>
      </div>

      <button onClick={handleCheckout} disabled={isLoading} className="w-full bg-indigo-600 text-white p-3 rounded font-semibold tracking-wide hover:bg-indigo-700 disabled:bg-gray-400">
        {isLoading ? "Processing Gateway..." : "Subscribe & Process Payment"}
      </button>
    </div>
  );
}
