'use client'

import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { Check, X } from 'lucide-react'

interface Plan {
  name: string
  price: string
  description: string
  features: string[]
  buttonText: string
  buttonVariant: 'primary' | 'secondary'
  popular?: boolean
}

export default function PricingPage() {
  const { user } = useAuth()
  const [isAnnual, setIsAnnual] = useState(false)

  const plans: Plan[] = [
    {
      name: 'Free',
      price: '$0',
      description: 'Perfect for getting started with SSAT practice',
      features: [
        '1 full test per day',
        '30 math questions daily',
        '18 analogy questions daily',
        '12 synonym questions daily',
        '7 reading passages daily',
        '1 writing prompt daily',
        'Basic question types',
        'PDF export'
      ],

      buttonText: 'Get Started Free',
      buttonVariant: 'secondary'
    },
    {
      name: 'Premium',
      price: isAnnual ? '$149' : '$14.99',
      description: 'Unlimited practice for serious SSAT preparation',
      features: [
        'Unlimited practice tests',
        'Unlimited math questions',
        'Unlimited analogy questions',
        'Unlimited synonym questions',
        'Unlimited reading passages',
        'Unlimited writing prompts',
        'Custom question generation',
        'Interactive answer checking',
        'PDF export'
      ],

      buttonText: user?.role === 'premium' ? 'Current Plan' : 'Upgrade to Premium',
      buttonVariant: 'primary',
      popular: true
    }
  ]

  const handleUpgrade = async (planName: string) => {
    if (planName === 'Free') {
      // Redirect to auth page for sign up/login
      window.location.href = '/auth'
    } else if (planName === 'Premium' && user?.role !== 'premium') {
      // TODO: Implement Stripe checkout
      alert('Payment integration coming soon!')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Choose Your SSAT Practice Plan
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Get unlimited AI-generated SSAT questions to ace your test. 
            Start free, upgrade when you're ready for unlimited practice.
          </p>
        </div>

        {/* Billing Toggle */}
        <div className="flex justify-center mb-8">
          <div className="bg-white rounded-lg p-1 shadow-sm">
            <div className="flex">
              <button
                onClick={() => setIsAnnual(false)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  !isAnnual
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Monthly
              </button>
              <button
                onClick={() => setIsAnnual(true)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  isAnnual
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Annual
                <span className="ml-1 text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full">
                  Save 17%
                </span>
              </button>
            </div>
          </div>
        </div>

        {/* Plans */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`relative bg-white rounded-2xl shadow-lg border-2 ${
                plan.popular
                  ? 'border-blue-500 shadow-xl'
                  : 'border-gray-200'
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                  <span className="bg-blue-600 text-white px-4 py-1 rounded-full text-sm font-medium">
                    Most Popular
                  </span>
                </div>
              )}

              <div className="p-8 flex flex-col h-full">
                <div className="text-center mb-6">
                  <h3 className="text-2xl font-bold text-gray-900 mb-2">
                    {plan.name}
                  </h3>
                  <div className="mb-4">
                    <span className="text-4xl font-bold text-gray-900">
                      {plan.price}
                    </span>
                    {plan.price !== '$0' && (
                      <span className="text-gray-600 ml-1">
                        /{isAnnual ? 'year' : 'month'}
                      </span>
                    )}
                  </div>
                  <p className="text-gray-600">{plan.description}</p>
                </div>

                {/* Features */}
                <div className="space-y-4 mb-8 flex-grow">
                  <h4 className="font-semibold text-gray-900 mb-3">
                    What's included:
                  </h4>
                  {plan.features.map((feature) => (
                    <div key={feature} className="flex items-start">
                      <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3 flex-shrink-0" />
                      <span className="text-gray-700">{feature}</span>
                    </div>
                  ))}
                  
                  {/* Premium features not included in free plan */}
                  {plan.name === 'Free' && (
                    <div className="mt-6 pt-4 border-t border-gray-200">
                      <h5 className="font-medium text-gray-900 mb-3">
                        Premium features (not included):
                      </h5>
                      <div className="space-y-2">
                        <div className="flex items-start">
                          <X className="h-5 w-5 text-gray-400 mt-0.5 mr-3 flex-shrink-0" />
                          <span className="text-gray-500">Interactive answer checking</span>
                        </div>
                        <div className="flex items-start">
                          <X className="h-5 w-5 text-gray-400 mt-0.5 mr-3 flex-shrink-0" />
                          <span className="text-gray-500">Unlimited practice</span>
                        </div>
                        <div className="flex items-start">
                          <X className="h-5 w-5 text-gray-400 mt-0.5 mr-3 flex-shrink-0" />
                          <span className="text-gray-500">Custom question generation</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* CTA Button */}
                <button
                  onClick={() => handleUpgrade(plan.name)}
                  disabled={user?.role === 'premium' && plan.name === 'Premium'}
                  className={`w-full py-3 px-6 rounded-lg font-medium transition-colors h-12 flex items-center justify-center mt-auto ${
                    plan.buttonVariant === 'primary'
                      ? 'bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-400'
                      : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                  }`}
                >
                  {plan.buttonText}
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* FAQ Section */}
        <div className="mt-16 max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-8">
            Frequently Asked Questions
          </h2>
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Can I cancel my subscription anytime?
              </h3>
              <p className="text-gray-600">
                Yes, you can cancel your subscription at any time. You'll continue to have access until the end of your billing period.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                What if I'm not satisfied?
              </h3>
              <p className="text-gray-600">
                We offer a 30-day money-back guarantee. If you're not completely satisfied, we'll refund your payment.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                How does the free plan work?
              </h3>
              <p className="text-gray-600">
                The free plan gives you 1 full SSAT test per day with all sections. Perfect for getting started with your SSAT preparation.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                What makes your questions different?
              </h3>
              <p className="text-gray-600">
                Our questions are AI-generated and specifically designed to match the SSAT format and difficulty levels. They're fresh, relevant, and help you practice effectively.
              </p>
            </div>
          </div>
        </div>
        
      </div>
    </div>
  )
} 