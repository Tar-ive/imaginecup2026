"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
    CheckCircle,
    Package,
    DollarSign,
    Repeat,
    X
} from "lucide-react"

interface OrderSummaryProps {
    ordersCreated: number
    totalValue: number
    orderIds: string[]
    onClose: () => void
    onSetRepeat?: (repeat: boolean) => void
}

export function OrderSummary({
    ordersCreated,
    totalValue,
    orderIds,
    onClose,
    onSetRepeat
}: OrderSummaryProps) {
    const [repeatNext, setRepeatNext] = useState(false)

    const formatCurrency = (val: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2
        }).format(val)
    }

    const handleRepeatToggle = () => {
        const newValue = !repeatNext
        setRepeatNext(newValue)
        onSetRepeat?.(newValue)
    }

    return (
        <Card className="border-green-200 bg-green-50">
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg flex items-center gap-2 text-green-700">
                        <CheckCircle size={20} />
                        Order Successfully Created!
                    </CardTitle>
                    <Button variant="ghost" size="sm" onClick={onClose}>
                        <X size={16} />
                    </Button>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Order Stats */}
                <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 rounded-lg bg-white border border-green-200">
                        <div className="flex items-center gap-2 text-green-600 mb-1">
                            <Package size={16} />
                            <span className="text-sm font-medium">Orders Created</span>
                        </div>
                        <div className="text-2xl font-bold text-green-800">
                            {ordersCreated}
                        </div>
                    </div>
                    <div className="p-3 rounded-lg bg-white border border-green-200">
                        <div className="flex items-center gap-2 text-green-600 mb-1">
                            <DollarSign size={16} />
                            <span className="text-sm font-medium">Total Value</span>
                        </div>
                        <div className="text-2xl font-bold text-green-800">
                            {formatCurrency(totalValue)}
                        </div>
                    </div>
                </div>

                {/* Order IDs */}
                {orderIds.length > 0 && (
                    <div className="p-3 rounded-lg bg-white border border-green-200">
                        <div className="text-sm font-medium text-green-700 mb-2">
                            Order References
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {orderIds.map((id) => (
                                <Badge key={id} variant="outline" className="bg-green-100 text-green-800 border-green-300">
                                    {id}
                                </Badge>
                            ))}
                        </div>
                    </div>
                )}

                {/* Repeat Option */}
                <div className="p-3 rounded-lg bg-white border border-green-200">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Repeat size={16} className="text-blue-600" />
                            <div>
                                <div className="text-sm font-medium text-gray-800">
                                    Auto-approve next time?
                                </div>
                                <div className="text-xs text-gray-500">
                                    Skip approval for similar orders in the future
                                </div>
                            </div>
                        </div>
                        <button
                            onClick={handleRepeatToggle}
                            className={`
                                relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                                ${repeatNext ? 'bg-green-500' : 'bg-gray-300'}
                            `}
                        >
                            <span
                                className={`
                                    inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                                    ${repeatNext ? 'translate-x-6' : 'translate-x-1'}
                                `}
                            />
                        </button>
                    </div>
                    {repeatNext && (
                        <div className="mt-2 text-xs text-green-600 bg-green-100 p-2 rounded">
                            ✓ Agent will auto-approve similar orders next time
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    )
}
