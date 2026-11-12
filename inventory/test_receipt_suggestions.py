from datetime import date
from django.test import SimpleTestCase
from inventory.receipt import receipt_drafts

class ReceiptSuggestionsTests(SimpleTestCase):
    def test_inline_quantity_and_unit_price_are_not_part_of_name(self):
        rows=receipt_drafts('Rice 1 x 9.00 9.00\n2 x MILK 7.00\nTOTAL 16.00', purchased_on=date(2026,11,12))
        self.assertEqual([(r['name'],str(r['quantity'])) for r in rows],[('Rice','1'),('MILK','2')])
        self.assertEqual(rows[0]['storage'],'pantry')
        self.assertEqual(rows[1]['expires_on'],date(2026,11,19))

    def test_receipt_date_and_default_quantity(self):
        row=receipt_drafts('Date: 11/12/2026\nPANEER 4.50')[0]
        self.assertEqual(row['quantity'],'1')
        self.assertEqual(row['expires_on'],date(2026,11,19))

    def test_weight_detail_and_unknown_items(self):
        rows=receipt_drafts('BANANAS 1.50\n1.12 lb @ $1.34/lb\nMYSTERY ITEM 3.00',purchased_on=date(2026,11,12))
        self.assertEqual(rows[0]['quantity'],'1.12')
        self.assertEqual(rows[0]['unit'],'lb')
        self.assertEqual(rows[1]['storage'],'')
        self.assertIsNone(rows[1]['expires_on'])

    def test_single_price_inline_layout(self):
        row=receipt_drafts('Rice 1 x 9.00',purchased_on=date(2026,11,12))[0]
        self.assertEqual(row['name'],'Rice')
        self.assertEqual(row['quantity'],'1')

    def test_storage_for_common_receipt_products(self):
        names={'FROZEN PEAS':'freezer','ICE CREAM':'freezer','OAT MILK':'fridge','PANEER':'fridge','COFFEE BEANS':'pantry','PROTEIN BARS':'pantry','DISH SOAP':'pantry'}
        for name,storage in names.items():
            with self.subTest(name=name):
                self.assertEqual(receipt_drafts(name+' 5.00')[0]['storage'],storage)

from inventory.tests import GroceryTestCase

class MultipleStockReceiptTests(GroceryTestCase):
    def test_each_receipt_keeps_its_purchase_date(self):
        self.client.force_login(self.owner)
        response=self.client.post(self.url('scan'),{'action':'review','receipt_text':[
            'Date: 11/11/2026\nMILK 4.50','Date: 11/12/2026\nPANEER 5.00']})
        rows=response.context['review'].initial
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]['expires_on'],date(2026,11,18))
        self.assertEqual(rows[1]['expires_on'],date(2026,11,19))

    def test_too_many_receipts_are_rejected(self):
        self.client.force_login(self.owner)
        response=self.client.post(self.url('scan'),{'action':'review','receipt_text':['MILK 4.50']*6})
        self.assertContains(response,'Use at most five receipts')
        self.assertIsNone(response.context['review'])
